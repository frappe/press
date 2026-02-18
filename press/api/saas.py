import json
from typing import TYPE_CHECKING

import frappe
from frappe.core.utils import find

from press.api.account import get_account_request_from_key
from press.press.doctype.site.erpnext_site import get_erpnext_domain
from press.press.doctype.site.saas_pool import get as get_pooled_saas_site
from press.press.doctype.site.saas_site import (
	SaasSite,
	get_default_team_for_app,
	get_saas_domain,
	get_saas_site_plan,
	set_site_in_subscription_docs,
)
from press.press.doctype.team.team import Team
from press.utils import log_error
from press.utils.telemetry import capture, identify

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site

# ----------------------------- SIGNUP APIs ---------------------------------


@frappe.whitelist(allow_guest=True)
def account_request(
	subdomain,
	email,
	first_name,
	last_name,
	country,
	app,
	url_args=None,
):
	"""
	return: Stripe setup intent and AR key if stripe flow, else None
	"""
	from frappe.utils.html_utils import clean_html

	email = email.strip().lower()
	frappe.utils.validate_email_address(email, True)

	if not check_subdomain_availability(subdomain, app):
		frappe.throw(f"Subdomain {subdomain} is already taken")

	all_countries = frappe.db.get_all("Country", pluck="name")
	country = find(all_countries, lambda x: x.lower() == country.lower())
	if not country:
		frappe.throw("Country field should be a valid country name")

	team = frappe.db.get_value("Team", {"user": email})
	if team and frappe.db.exists("Invoice", {"team": team, "status": "Unpaid", "type": "Subscription"}):
		frappe.throw(f"Account {email} already exists with unpaid invoices")

	current_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"saas": True,
				"saas_app": app,
				"erpnext": False,
				"subdomain": subdomain,
				"email": email,
				"role": "Press Admin",
				"first_name": clean_html(first_name),
				"last_name": clean_html(last_name),
				"country": country,
				"url_args": url_args or json.dumps({}),
				"send_email": True,
			}
		)
		site_name = account_request.get_site_name()
		identify(
			site_name,
			app=account_request.saas_app,
			source=json.loads(url_args).get("source") if url_args else "fc",
		)
		account_request.insert(ignore_permissions=True)
		capture("completed_server_account_request", "fc_product_trial", site_name)
	except Exception as e:
		log_error("Account Request Creation Failed", data=e)
		raise
	finally:
		frappe.set_user(current_user)

	create_or_rename_saas_site(app, account_request)


def create_or_rename_saas_site(app, account_request):
	"""
	Creates site for Saas App. These are differentiated by `standby_for` field in site doc
	"""
	current_user = frappe.session.user
	current_session_data = frappe.session.data
	frappe.set_user("Administrator")

	try:
		enable_hybrid_pools = frappe.db.get_value("Saas Settings", app, "enable_hybrid_pools")
		hybrid_saas_pool = get_hybrid_saas_pool(account_request) if enable_hybrid_pools else ""

		pooled_site = get_pooled_saas_site(app, hybrid_saas_pool)
		if pooled_site:
			SaasSite(site=pooled_site, app=app).rename_pooled_site(account_request)
		else:
			saas_site = SaasSite(
				account_request=account_request, app=app, hybrid_saas_pool=hybrid_saas_pool
			).insert(ignore_permissions=True)
			set_site_in_subscription_docs(saas_site.subscription_docs, saas_site.name)

		capture("completed_server_site_created", "fc_product_trial", account_request.get_site_name())
	except Exception as e:
		log_error("Saas Site Creation or Rename failed", data=e)

	finally:
		frappe.set_user(current_user)
		frappe.session.data = current_session_data


@frappe.whitelist()
def new_saas_site(subdomain, app):
	frappe.only_for("System Manager")

	pooled_site = get_pooled_saas_site(app)
	if pooled_site:
		site = SaasSite(site=pooled_site, app=app).rename_pooled_site(subdomain=subdomain)
	else:
		site = SaasSite(app=app, subdomain=subdomain).insert(ignore_permissions=True)
		site.create_subscription(get_saas_site_plan(app))

	site.reload()
	site.team = get_default_team_for_app(app)
	site.save(ignore_permissions=True)

	frappe.db.commit()

	return site


def get_hybrid_saas_pool(account_request):
	"""
	1. Get all hybrid pools and their rules
	2. Filter based on rules and return Hybrid pool
	3. Returns the first rule match
	return: The hybrid pool name that site belongs to based on the Account Request
	conditions
	"""
	hybrid_pool = ""
	all_pools = frappe.get_all("Hybrid Saas Pool", {"app": account_request.saas_app}, pluck="name")
	ar_rules = frappe.get_all(
		"Account Request Rules",
		{"parent": ("in", all_pools)},
		["parent", "field", "condition", "value"],
		group_by="parent",
	)

	for rule in ar_rules:
		eval_locals = eval_locals = dict(
			account_request=account_request,
		)

		if frappe.safe_eval(
			f"account_request.{rule.field} {rule.condition} '{rule.value}'", None, eval_locals
		):
			hybrid_pool = rule.parent
			return hybrid_pool  # noqa: RET504

	return hybrid_pool


@frappe.whitelist(allow_guest=True)
def check_subdomain_availability(subdomain, app):
	"""
	Checks if subdomain is available to create a new site
	"""
	# Only for ERPNext domains

	if len(subdomain) <= 4:
		return False

	banned_domains = frappe.get_all("Blocked Domain", {"block_for_all": 1}, pluck="name")
	if banned_domains and subdomain in banned_domains:
		return False

	exists = bool(
		frappe.db.exists("Blocked Domain", {"name": subdomain, "root_domain": get_erpnext_domain()})
		or frappe.db.exists(
			"Site",
			{
				"subdomain": subdomain,
				"domain": get_saas_domain(app),
				"status": ("!=", "Archived"),
			},
		)
	)
	if exists:
		return False

	return True


@frappe.whitelist(allow_guest=True)
def setup_account(key, business_data=None):
	"""
	Includes the data collection step in setup-account.html
	"""
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	capture(
		"init_server_setup_account",
		"fc_product_trial",
		account_request.get_site_name(),
	)
	frappe.set_user("Administrator")

	if business_data:
		business_data = frappe.parse_json(business_data)

	if isinstance(business_data, dict):
		business_data = {
			key: business_data.get(key)
			for key in [
				"company",
				"no_of_employees",
				"industry",
				"no_of_users",
				"designation",
				"phone_number",
				"referral_source",
				"agreed_to_partner_consent",
			]
		}

	account_request.update(business_data)
	account_request.save(ignore_permissions=True)

	create_marketplace_subscription(account_request)
	capture(
		"completed_server_setup_account",
		"fc_product_trial",
		account_request.get_site_name(),
	)


@frappe.whitelist(allow_guest=True)
def headless_setup_account(key):
	"""
	Ignores the data collection step in setup-account.html
	"""
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	capture(
		"init_server_setup_account",
		"fc_product_trial",
		account_request.get_site_name(),
	)
	frappe.set_user("Administrator")

	create_marketplace_subscription(account_request)
	# create team and enable the subscriptions for site
	capture(
		"completed_server_setup_account",
		"fc_product_trial",
		account_request.get_site_name(),
	)

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/prepare-site?key={key}&app={account_request.saas_app}"


def create_marketplace_subscription(account_request):
	"""
	Create team, subscription for site and Saas Subscription
	"""
	team_doc = create_team(account_request)
	site_name = frappe.db.get_value("Site", {"account_request": account_request.name})
	if site_name:
		frappe.db.set_value("Site", site_name, "team", team_doc.name)

	subscription = frappe.db.exists("Subscription", {"document_name": site_name})
	if subscription:
		frappe.db.set_value("Subscription", subscription, "team", team_doc.name)

	marketplace_subscriptions = frappe.get_all(
		"Subscription",
		{"document_type": "Marketplace App", "site": site_name, "enabled": 0},
		pluck="name",
	)
	for subscription in marketplace_subscriptions:
		frappe.db.set_value(
			"Subscription",
			subscription,
			{"enabled": 1, "team": team_doc.name},
		)

	frappe.set_user(team_doc.user)
	frappe.local.login_manager.login_as(team_doc.user)

	return site_name


def create_team(account_request, get_stripe_id=False):
	"""
	Create team and return doc
	"""
	email = account_request.email

	if not frappe.db.exists("Team", {"user": email}):
		team_doc = Team.create_new(
			account_request,
			account_request.first_name,
			account_request.last_name,
			country=account_request.country,
			is_us_eu=account_request.is_us_eu,
			via_erpnext=True,
			user_exists=frappe.db.exists("User", email),
		)
	else:
		team_doc = frappe.get_doc("Team", {"user": email})

	if get_stripe_id:
		return team_doc.stripe_customer_id

	return team_doc


@frappe.whitelist(allow_guest=True)
def get_site_status(key, app=None):
	"""
	return: Site status
	"""
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	domain = get_saas_domain(app) if app else get_erpnext_domain()

	site = frappe.db.get_value(
		"Site",
		{"subdomain": account_request.subdomain, "domain": domain, "status": "Active"},
		["status", "subdomain", "name"],
		as_dict=1,
	)
	if site:
		capture("completed_site_allocation", "fc_product_trial", site.name)
		return site
	return {"status": "Pending"}


@frappe.whitelist(allow_guest=True)
def get_site_url_and_sid(key, app=None):
	"""
	return: Site url and session id for login-redirect
	"""
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	domain = get_saas_domain(app) if app else get_erpnext_domain()

	name = frappe.db.get_value("Site", {"subdomain": account_request.subdomain, "domain": domain})
	site: "Site" = frappe.get_doc("Site", name)
	if site.additional_system_user_created:
		return site.login_as_team()
	return site.login_as_admin()
