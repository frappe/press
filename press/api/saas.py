import frappe
import json
from frappe.core.utils import find
from frappe.core.doctype.user.user import test_password_strength
from frappe.utils.password import get_decrypted_password
from press.press.doctype.team.team import Team
from press.api.account import get_account_request_from_key
from press.utils import log_error

from press.press.doctype.site.saas_site import (
	SaasSite,
	get_default_team_for_app,
	get_saas_domain,
	get_saas_site_plan,
	set_site_in_subscription_docs,
)
from press.press.doctype.site.saas_pool import get as get_pooled_saas_site
from press.press.doctype.site.erpnext_site import get_erpnext_domain
from press.utils.billing import clear_setup_intent
from press.utils.telemetry import capture, identify


# ----------------------------- SIGNUP APIs ---------------------------------


@frappe.whitelist(allow_guest=True)
def account_request(
	subdomain,
	email,
	password,
	first_name,
	last_name,
	country,
	app,
	company=None,
	phone_number=None,
	url_args=None,
):
	"""
	return: Stripe setup intent and AR key if stripe flow, else None
	"""
	email = email.strip().lower()
	frappe.utils.validate_email_address(email, True)

	if not check_subdomain_availability(subdomain, app):
		frappe.throw(f"Subdomain {subdomain} is already taken")

	password_validation = validate_password(password, first_name, last_name, email)
	if not password_validation.get("validation_passed"):
		frappe.throw(password_validation.get("suggestion")[0])

	all_countries = frappe.db.get_all("Country", pluck="name")
	country = find(all_countries, lambda x: x.lower() == country.lower())
	if not country:
		frappe.throw("Country field should be a valid country name")

	try:
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"saas": True,
				"saas_app": app,
				"erpnext": False,
				"subdomain": subdomain,
				"email": email,
				"password": password,
				"role": "Press Admin",
				"first_name": first_name,
				"last_name": last_name,
				"company": company,
				"phone_number": phone_number,
				"country": country,
				"url_args": url_args or json.dumps({}),
				"send_email": True,
			}
		)
		site_name = account_request.get_site_name()
		identify(
			site_name,
			app=account_request.saas_app,
		)
		account_request.insert(ignore_permissions=True)
		capture("completed_server_account_request", "fc_saas", site_name)
	except Exception as e:
		log_error("Account Request Creation Failed", e)
		raise

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
		hybrid_saas_pool = (
			get_hybrid_saas_pool(account_request) if enable_hybrid_pools else ""
		)

		pooled_site = get_pooled_saas_site(app, hybrid_saas_pool)
		if pooled_site:
			SaasSite(site=pooled_site, app=app).rename_pooled_site(account_request)
		else:
			saas_site = SaasSite(
				account_request=account_request, app=app, hybrid_saas_pool=hybrid_saas_pool
			).insert(ignore_permissions=True)
			set_site_in_subscription_docs(saas_site.subscription_docs, saas_site.name)
			saas_site.create_subscription(get_saas_site_plan(app))

		capture("completed_server_site_created", "fc_saas", account_request.get_site_name())
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


@frappe.whitelist()
def get_saas_site_status(site):
	if frappe.db.exists("Site", site):
		return {"site": site, "status": frappe.db.get_value("Site", site, "status")}

	return {"site": site, "status": "Pending"}


def get_hybrid_saas_pool(account_request):
	"""
	1. Get all hybrid pools and their rules
	2. Filter based on rules and return Hybrid pool
	3. Returns the first rule match
	return: The hybrid pool name that site belongs to based on the Account Request
	conditions
	"""
	hybrid_pool = ""
	all_pools = frappe.get_all(
		"Hybrid Saas Pool", {"app": account_request.saas_app}, pluck="name"
	)
	ar_rules = frappe.get_all(
		"Account Request Rules",
		{"parent": ("in", all_pools)},
		["parent", "field", "condition", "value"],
		group_by="parent",
	)

	for rule in ar_rules:
		if eval(f"account_request.{rule.field} {rule.condition} '{rule.value}'"):
			hybrid_pool = rule.parent
			return hybrid_pool

	return hybrid_pool


@frappe.whitelist(allow_guest=True)
def validate_password(password, first_name, last_name, email):
	passed = True
	suggestion = None

	user_data = (first_name, last_name, email)
	result = test_password_strength(password, "", None, user_data)
	feedback = result.get("feedback", None)

	if feedback and not feedback.get("password_policy_validation_passed", False):
		passed = False
		suggestion = feedback.get("suggestions")

	return {"validation_passed": passed, "suggestion": suggestion}


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
		frappe.db.exists(
			"Blocked Domain", {"name": subdomain, "root_domain": get_erpnext_domain()}
		)
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
def validate_account_request(key):
	if not key:
		frappe.throw("Request Key not provided")

	app = frappe.db.get_value("Account Request", {"request_key": key}, "saas_app")

	#saas generator uses app titla as its name
	# so we need to get the app title
 	
  	
   	
	app_title = frappe.db.get_value("Saas App",app,"title")
	app_title = "-".join(app_title.split(" ")).lower()
	headless, route = frappe.db.get_value(
		"Saas Setup Account Generator", app_title, ["headless", "route"]
	)

	if headless:
		headless_setup_account(key)
	else:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = f"/{route}?key={key}"


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
		"fc_saas",
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
		"fc_saas",
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
		"fc_saas",
		account_request.get_site_name(),
	)
	frappe.set_user("Administrator")

	create_marketplace_subscription(account_request)
	# create team and enable the subscriptions for site
	capture(
		"completed_server_setup_account",
		"fc_saas",
		account_request.get_site_name(),
	)

	frappe.local.response["type"] = "redirect"
	frappe.local.response[
		"location"
	] = f"/prepare-site?key={key}&app={account_request.saas_app}"


def create_marketplace_subscription(account_request):
	"""
	Create team, subscription for site and Saas Subscription
	"""
	team_doc = create_team(account_request)
	site_name = frappe.db.get_value("Site", {"account_request": account_request.name})
	site = frappe.get_doc("Site", site_name)
	site.team = team_doc.name
	site.save()

	if not frappe.db.exists("Subscription", {"document_name": site_name}):
		subscription = site.subscription
		if subscription:
			subscription.team = team_doc.name
			subscription.save()

	subscriptions = frappe.get_all(
		"Marketplace App Subscription",
		{"site": site_name, "status": "Disabled"},
		pluck="name",
	)
	for subscription in subscriptions:
		frappe.db.set_value(
			"Marketplace App Subscription",
			subscription,
			{"status": "Active", "team": site.team},
		)

	frappe.set_user(team_doc.user)
	frappe.local.login_manager.login_as(team_doc.user)

	return site.name


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
			password=get_decrypted_password("Account Request", account_request.name, "password"),
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
		capture("completed_site_allocation", "fc_saas", site.name)
		return site
	else:
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

	name = frappe.db.get_value(
		"Site", {"subdomain": account_request.subdomain, "domain": domain}
	)
	site = frappe.get_doc("Site", name)
	return {
		"url": f"https://{site.name}",
		"sid": site.login(),
	}


# ------------------ Stripe setup ------------------- #


@frappe.whitelist(allow_guest=True)
def setup_intent_success(setup_intent, account_request_key):
	"""
	Create a team with card and create site
	"""
	account_request = get_account_request_from_key(account_request_key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	team = frappe.get_doc("Team", account_request.email)
	frappe.set_user(account_request.email)
	clear_setup_intent()

	team.create_payment_method(
		json.loads(setup_intent)["payment_method"], set_default=True
	)
	account_request.send_verification_email()
	create_or_rename_saas_site(account_request.saas_app, account_request)
