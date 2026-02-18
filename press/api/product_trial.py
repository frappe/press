# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random

import frappe
import frappe.utils
from frappe.rate_limiter import rate_limit

from press.api.account import get_account_request_from_key
from press.press.doctype.team.team import Team
from press.saas.doctype.product_trial.product_trial import ProductTrial, send_verification_mail_for_login
from press.utils.telemetry import capture


def _get_active_site(product: str, team: str | None) -> str | None:
	if team is None:
		return None
	product_trial_linked_sites = frappe.get_all(
		"Product Trial Request",
		{"product_trial": product, "team": team, "status": ["not in", ["Pending", "Error", "Expired"]]},
		pluck="site",
	)
	if not product_trial_linked_sites:
		return None
	existing_sites = frappe.get_all(
		"Site",
		{
			"name": ["in", product_trial_linked_sites],
			"status": ["!=", "Archived"],
		},
		pluck="name",
		limit=1,
	)
	if len(existing_sites) > 0:
		return existing_sites[0]
	return None


@frappe.whitelist(allow_guest=True)
def send_verification_code_for_login(email: str, product: str):
	is_user_exists = frappe.db.exists("Team", {"user": email}) and _get_active_site(
		product, frappe.db.get_value("Team", {"user": email}, "name")
	)
	if not is_user_exists:
		frappe.throw("You have no active sites for this product. Please try signing up.")
	# generate otp and store in redis
	otp = str(random.randint(100000, 999999))
	frappe.cache.set_value(
		f"product_trial_login_verification_code:{email}",
		frappe.utils.sha256_hash(otp),
		expires_in_sec=300,
	)

	send_verification_mail_for_login(email, product, otp)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=300)
def login_using_code(email: str, product: str, code: str):
	team_exists = frappe.db.exists("Team", {"user": email})
	site = _get_active_site(product, frappe.db.get_value("Team", {"user": email}, "name"))
	if not team_exists:
		frappe.throw("You have no active sites for this product. Please try signing up.")

	# check if team has 2fa enabled and active
	team = frappe.get_value("Team", {"user": email}, ["name", "enforce_2fa", "enabled"], as_dict=True)
	if not team.enabled:
		frappe.throw("Your account is disabled. Please contact support.")
	if team.enforce_2fa:
		frappe.throw("Your account has 2FA enabled. Please go to frappecloud.com to login.")

	# validate code
	code_hash_from_cache = frappe.cache.get_value(f"product_trial_login_verification_code:{email}")
	if not code_hash_from_cache:
		frappe.throw("OTP has expired. Please try again.")
	if frappe.utils.sha256_hash(str(code)) != code_hash_from_cache:
		frappe.throw("Invalid OTP. Please try again.")

	# remove code from cache
	frappe.cache.delete_value(f"product_trial_login_verification_code:{email}")

	# login as user
	frappe.set_user(email)
	frappe.local.login_manager.login_as(email)

	# send the product trial request name
	return frappe.get_value(
		"Product Trial Request",
		{"product_trial": product, "team": team.name, "site": site},
		pluck="name",
	)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def get_account_request_for_product_signup():
	return frappe.db.get_value("Account Request", {"email": frappe.session.user}, "name")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def setup_account(key: str, country: str | None = None):
	ar = get_account_request_from_key(key)
	if not ar:
		frappe.throw("Invalid or Expired Key")
	if not ar.product_trial:
		frappe.throw("Invalid Product Trial")

	if country:
		ar.country = country
		ar.save(ignore_permissions=True)

	if not ar.country:
		frappe.throw("Please provide a valid country name")

	frappe.set_user("Administrator")
	# check if team already exists
	if frappe.db.exists("Team", {"user": ar.email}):
		# Update first name and last name
		team = frappe.get_doc("Team", {"user": ar.email})
		team.first_name = ar.first_name
		team.last_name = ar.last_name
		team.save(ignore_permissions=True)
	# create team
	else:
		# check if user exists
		is_user_exists = frappe.db.exists("User", ar.email)
		team = Team.create_new(
			account_request=ar,
			first_name=ar.first_name,
			last_name=ar.last_name,
			country=ar.country,
			is_us_eu=ar.is_us_eu,
			user_exists=is_user_exists,
		)
	# Telemetry: Created account
	capture("completed_signup", "fc_product_trial", ar.email)
	# login
	frappe.set_user(ar.email)
	frappe.local.login_manager.login_as(ar.email)
	if _get_active_site(ar.product_trial, team.name):
		return {
			"account_request": ar.name,
			"location": f"/dashboard/saas/{ar.product_trial}/login-to-site?account_request={ar.name}",
		}

	return {
		"account_request": ar.name,
		"location": f"/dashboard/saas/{ar.product_trial}/setup?account_request={ar.name}",
	}


def _get_existing_trial_request(product: str, team: str):
	return frappe.get_value(
		"Product Trial Request",
		{"team": team, "status": ["not in", ["Error", "Expired", "Site Created"]], "product_trial": product},
		["name", "site"],
		as_dict=True,
	)


@frappe.whitelist(methods=["POST"])
def get_request(product: str, account_request: str | None = None) -> dict:
	from frappe.core.utils import find

	from press.utils import get_nearest_cluster

	team = frappe.local.team()
	cluster = "Default"

	# validate if there is already a site
	if site := _get_active_site(product, team.name):
		site_request = frappe.get_doc(
			"Product Trial Request", {"product_trial": product, "team": team, "site": site}
		)
	elif request := _get_existing_trial_request(product, team.name):
		site_request = frappe.get_doc("Product Trial Request", request.name)
	else:
		site_request = frappe.new_doc(
			"Product Trial Request",
			product_trial=product,
			team=team.name,
			account_request=account_request,
		).insert(ignore_permissions=True)

	product_trial: ProductTrial = frappe.get_doc("Product Trial", product)
	if product_trial.enable_hybrid_pooling:
		cluster = ""
		fields = [rule.field for rule in product_trial.hybrid_pool_rules]
		acc_req = (
			frappe.db.get_value(
				"Account Request",
				account_request,
				fields,
				as_dict=True,
			)
			if account_request
			else None
		)

		for rule in product_trial.hybrid_pool_rules:
			value = acc_req.get(rule.field) if acc_req else None
			if not value:
				break

			if rule.value == value:
				cluster = rule.preferred_cluster
				break

		if not cluster:
			cluster = get_nearest_cluster()
	else:
		cluster = get_nearest_cluster()
	domain = frappe.db.get_value("Product Trial", product, "domain")
	prefilled_subdomain = product_trial.get_prefilled_subdomain(account_request)
	cluster_domains = frappe.db.get_all(
		"Root Domain", {"name": ("like", f"%.{domain}")}, ["name", "default_cluster as cluster"]
	)

	cluster_domain = find(
		cluster_domains,
		lambda d: d.cluster == cluster if cluster else False,
	)

	return {
		"name": site_request.name,
		"site": site_request.site,
		"product_trial": site_request.product_trial,
		"domain": cluster_domain["name"] if cluster_domain else domain,
		"status": site_request.status,
		"prefilled_subdomain": prefilled_subdomain,
	}
