import frappe
from frappe.model.naming import getseries
import stripe
import json
from frappe.core.utils import find
from frappe.utils.password import get_decrypted_password
from press.api.billing import create_payment_intent_for_prepaid_app
from press.api.site import overview, protected, get
from press.api.bench import options
from press.utils import unique
from press.press.doctype.app.app import new_app as new_app_doc
from press.press.doctype.team.team import Team
from press.api.account import get_account_request_from_key
from press.saas.doctype.saas_app_plan.saas_app_plan import (
	get_app_plan_features,
)
from press.utils import get_current_team
from press.agent import Agent

from press.press.doctype.site.saas_site import (
	SaasSite,
	get_saas_domain,
	get_saas_plan,
	get_saas_site_plan,
)
from press.press.doctype.site.saas_pool import get as get_pooled_saas_site
from press.press.doctype.site.erpnext_site import get_erpnext_domain
from press.utils.billing import (
	clear_setup_intent,
	get_erpnext_com_connection,
)


@frappe.whitelist()
def get_saas_apps():
	"""
	return: All available saas apps with description and info
	"""
	apps = frappe.get_all(
		"Saas App",
		{"status": "Published"},
		["name", "title", "image", "description", "signup_url"],
	)
	return apps


@frappe.whitelist()
def get_apps():
	"""
	return: All apps created by developer
	"""
	apps = frappe.get_all(
		"Saas App", {"team": get_current_team()}, ["name", "title", "status"]
	)

	for app in apps:
		app["count"] = frappe.db.count(
			"Saas App Subscription", {"status": ("!=", "Disabled"), "app": app.name}
		)

	return apps


@frappe.whitelist()
@protected("Saas App")
def get_app(name):
	"""
	return: Fields from saas app
	"""
	return frappe.get_doc("Saas App", name)


@frappe.whitelist()
@protected("Saas App")
def get_plans(name):
	"""
	return: Saas plans for app
	"""
	plans = frappe.db.get_all(
		"Saas App Plan",
		{"app": name, "is_free": False},
		["name", "plan", "plan_title", "site_plan", "enabled"],
		order_by="creation asc",
	)

	for plan in plans:
		features = get_app_plan_features(plan.name)
		plan.features = [{"id": idx, "value": value} for idx, value in enumerate(features)]
		plan.update(
			frappe.db.get_list(
				"Plan", {"name": plan.plan}, ["plan_title", "price_usd", "price_inr"]
			)[0]
		)

	site_plans = frappe.get_all("Plan", {"document_type": "Site"}, pluck="name")

	return {"saas_plans": plans, "site_plans": site_plans}


@frappe.whitelist()
@protected("Saas App")
def edit_plan(plan, name):
	"""
	Edit saas plan and initial plan details
	"""
	# change saas plan fields(site_plan and features)
	saas_plan_doc = frappe.get_doc("Saas App Plan", plan["name"])
	saas_plan_doc.site_plan = plan["site_plan"]
	saas_plan_doc.features = []
	features = [feat["value"] for feat in plan["features"]]
	for feature in features:
		saas_plan_doc.append("features", {"description": feature})
	saas_plan_doc.save(ignore_permissions=True)

	# change initial plan fields(name, prices)
	plan_doc = frappe.get_doc("Plan", saas_plan_doc.plan)
	plan_doc.plan_title = plan["plan_title"]
	plan_doc.price_usd = plan["price_usd"]
	plan_doc.price_inr = plan["price_inr"]
	plan_doc.save(ignore_permissions=True)


@frappe.whitelist()
@protected("Saas App")
def create_plan(plan, name):
	"""
	Create plan
	"""
	# create plan
	plan_doc = frappe.get_doc(
		{
			"doctype": "Plan",
			"plan_title": plan["title"],
			"name": f"saas-plan-{plan['app']}-" + getseries(f"saas-plan-{plan['app']}", 3),
			"document_type": "Saas App",
			"price_usd": plan["usd"],
			"price_inr": plan["inr"],
		}
	).insert()

	# create saas app plan
	saas_plan_doc = frappe.get_doc(
		{
			"doctype": "Saas App Plan",
			"plan": plan_doc.name,
			"site_plan": plan["site_plan"],
			"app": plan["app"],
			"enabled": 1,
		}
	)

	for feat in plan["features"]:
		saas_plan_doc.append("features", {"description": feat["value"]})

	saas_plan_doc.insert()


@frappe.whitelist()
def get_sites(app):
	sites = frappe.db.sql(
		f"""
		SELECT
			site.name, site.status, subscription.plan, subscription.team
		FROM
			tabSite site
		LEFT JOIN
			`tabSaas App Subscription` subscription
		ON
			site.name = subscription.site
		WHERE
			(subscription.app = '{app}')
	""",
		as_dict=True,
	)
	return sites


@frappe.whitelist()
@protected("Saas App Subscription")
def get_plans_info(name):
	"""
	return: Subscription information for site (plans, active plan, trial)
	"""
	app, site, app_name = frappe.db.get_value(
		"Saas App Subscription", name, ["app", "site", "app_name"]
	)
	saas_app = frappe.get_doc("Saas App", app)
	plans = saas_app.get_plans(site)
	trial_date = frappe.db.get_value("Site", site, "trial_end_date")

	site_data = {
		"plans": plans,
		"trial_end_date": trial_date,
		"site": site,
		"app_name": app_name,
	}

	return site_data


@frappe.whitelist()
def get_subscriptions():
	return frappe.get_all(
		"Saas App Subscription",
		{"status": ("!=", "Disabled"), "team": get_current_team()},
		["name", "status", "site", "app_name", "plan"],
	)


@frappe.whitelist()
@protected("Saas App Subscription")
def subscription_overview(name):
	subscription = frappe.get_doc("Saas App Subscription", name)
	return {
		"subscription": subscription,
		"site_overview": overview(subscription.site),
		"site": get(subscription.site),
	}


@frappe.whitelist()
@protected("Saas App Subscription")
def change_plan(name, new_plan, option):
	subscription = frappe.get_doc("Saas App Subscription", name)

	if "postpaid" == frappe.db.get_value(
		"Saas Settings", subscription.app, "billing_type"
	):
		# create payment intent and return
		amount = frappe.db.get_value(
			"Plan", new_plan["plan"], f"price_{get_current_team(True).currency.lower()}"
		)
		amount = amount * 12 if option == "Yearly" else amount
		intent = create_payment_intent_for_prepaid_app(
			int(amount),
			subscription.app,
			"prepaid_saas",
			option,
			new_plan["name"],
			subscription.name,
		)
		intent.update({"payment_type": "postpaid"})

		return intent
	else:
		subscription.change_plan(new_plan["name"])


# do this after payment succeeds
def smb_plan_change(subscription, new_plan):
	if subscription.app == "erpnext_smb":
		site = frappe.get_doc("Site", subscription.site)
		site.update_site_config({"plan": new_plan["plan_title"]})

		server = frappe.db.get_value("Site", subscription.site, "server")
		agent = Agent(server_type="Server", server=server)
		data = {
			"plan": new_plan["plan"],
		}

		return agent.create_agent_job(
			"Update Saas Plan",
			f"benches/{site.bench}/sites/{site.name}/update/saas",
			data=data,
			bench=site.bench,
			site=site.name,
		)


@frappe.whitelist()
def get_benches(saas_app):
	groups = frappe.get_all(
		"Release Group",
		{"team": get_current_team(), "saas_app": saas_app},
		["name", "title"],
	)

	for group in groups:
		group["active_sites"] = frappe.db.count(
			"Site", {"group": group["name"], "status": "Active"}
		)
		group["broken_sites"] = frappe.db.count(
			"Site", {"group": group["name"], "status": "Broken"}
		)
		group["suspended_sites"] = frappe.db.count(
			"Site", {"group": group["name"], "status": "Suspended"}
		)

		active_benches = frappe.get_all(
			"Bench",
			{"group": group["name"], "status": "Active"},
			limit=1,
			order_by="creation desc",
		)
		group["status"] = "Active" if active_benches else "Awaiting Deploy"

	data = {
		"groups": groups,
		"active_group": frappe.db.get_value("Saas Settings", saas_app, "group"),
	}

	return data


@frappe.whitelist()
def options_for_saas_app():
	versions = options(only_by_current_team=True)["versions"]
	filtered_apps = []
	for version in versions:
		# Remove Frappe Framework
		version["apps"] = [app for app in version["apps"] if app["name"] != "frappe"]

		for app in version["apps"]:
			if not saas_app_exists(app["name"]):
				for source in app["sources"]:
					source["version"] = version["name"]
				filtered_apps.append(app)

			else:
				saas_app = frappe.get_doc("Saas App", app["name"])
				saas_versions = [v.version for v in saas_app.sources]

				if version["name"] not in saas_versions:
					for source in app["sources"]:
						source["version"] = version["name"]
					filtered_apps.append(app)

	aggregated_sources = {}

	for app in filtered_apps:
		aggregated_sources.setdefault(app["name"], []).extend(app["sources"])
		# Remove duplicate sources
		aggregated_sources[app["name"]] = unique(
			aggregated_sources[app["name"]], lambda x: x["name"]
		)

	saas_options = []
	for app_name, sources in aggregated_sources.items():
		app = find(filtered_apps, lambda x: x["name"] == app_name)
		saas_options.append(
			{
				"name": app_name,
				"sources": sources,
				"source": app["source"],
				"title": app["title"],
			}
		)

	return saas_options


def saas_app_exists(app: str) -> bool:
	"""Returns `True` if this `app` already exists as Saas App or else `False`"""
	return frappe.db.exists("Saas App", app)


@frappe.whitelist()
def new_app(app):
	name = app["name"]
	team = get_current_team()

	if frappe.db.exists("App", name):
		app_doc = frappe.get_doc("App", name)
	else:
		app_doc = new_app_doc(name, app["title"])

	source = app_doc.add_source(
		app["version"],
		app["repository_url"],
		app["branch"],
		team,
		app["github_installation_id"],
	)

	return add_app(source.name, app_doc.name)


@frappe.whitelist()
def add_app(source, app):
	if not saas_app_exists(app):
		supported_versions = frappe.get_all(
			"App Source Version", filters={"parent": source}, pluck="version"
		)
		saas_app = frappe.get_doc(
			doctype="Saas App",
			app=app,
			team=get_current_team(),
			description="Please add a short description about your app here...",
			sources=[{"version": v, "source": source} for v in supported_versions],
		).insert()

	else:
		saas_app = frappe.get_doc("Saas App", app)

		if saas_app.team != get_current_team():
			frappe.throw(
				f"The app {saas_app.name} already exists and is owned by some other team."
			)

	# Versions on saas_app
	versions = [v.version for v in saas_app.sources]

	version_difference = set(versions)
	if version_difference:
		# App source contains version not yet in saas_app
		for version in version_difference:
			saas_app.append("sources", {"source": source, "version": version})
			saas_app.save()
	else:
		frappe.throw("Compatible Frappe version not selected.")

	return saas_app.name


@frappe.whitelist()
@protected("Saas App")
def update_settings(name, active_bench):
	active_benches = frappe.get_all(
		"Bench",
		{"group": active_bench, "status": "Active"},
		["cluster", "group"],
		limit=1,
		order_by="creation desc",
	)
	if active_benches:
		frappe.db.set_value("Saas Settings", name, "group", active_benches[0].group)
		frappe.db.set_value("Saas Settings", name, "cluster", active_benches[0].cluster)
	else:
		frappe.throw(
			"This bench is not deployed, please deploy the bench before setting it as default."
		)

	return name


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
	phone_number=None,
	url_args=None,
	stripe_setup=False,
):
	email = email.strip().lower()
	frappe.utils.validate_email_address(email, True)

	if not check_subdomain_availability(subdomain, app):
		frappe.throw(f"Subdomain {subdomain} is already taken")

	all_countries = frappe.db.get_all("Country", pluck="name")
	country = find(all_countries, lambda x: x.lower() == country.lower())
	if not country:
		frappe.throw("Country filed should be a valid country name")

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
			"phone_number": phone_number,
			"country": country,
			"url_args": url_args or json.dumps({}),
			"send_email": not stripe_setup,
		}
	).insert(ignore_permissions=True)

	if stripe_setup:
		frappe.set_user("Administrator")
		stripe.api_key = get_decrypted_password(
			"Stripe Settings",
			frappe.db.get_single_value("Press Settings", "stripe_account"),
			"secret_key",
			raise_exception=False,
		)
		customer_id = create_team(account_request, get_stripe_id=True)

		return {
			"account_request_key": account_request.request_key,
			"setup_intent": stripe.SetupIntent.create(
				customer=customer_id, payment_method_types=["card"]
			),
		}
	else:
		create_or_rename_saas_site(app, account_request)


def create_or_rename_saas_site(app, account_request):
	current_user = frappe.session.user
	current_session_data = frappe.session.data
	frappe.set_user("Administrator")

	try:
		pooled_site = get_pooled_saas_site(app)
		if pooled_site:
			# Rename a standby site
			SaasSite(site=pooled_site, app=app).rename_pooled_site(account_request)
		else:
			# Create a new site if pooled sites aren't available
			saas_site = SaasSite(account_request=account_request, app=app).insert(
				ignore_permissions=True
			)
			saas_site.create_subscription(get_saas_site_plan(app))
	finally:
		frappe.set_user(current_user)
		frappe.session.data = current_session_data


@frappe.whitelist(allow_guest=True)
def check_subdomain_availability(subdomain, app):
	# Only for ERPNext domains

	erpnext_com = get_erpnext_com_connection()
	result = erpnext_com.post_api(
		"central.www.signup.check_subdomain_availability", {"subdomain": subdomain}
	)
	if result:
		return False

	exists = bool(
		frappe.db.exists(
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
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

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
				"referral_source",
				"agreed_to_partner_consent",
			]
		}

	account_request.update(business_data)
	account_request.save(ignore_permissions=True)

	create_saas_subscription(account_request)


@frappe.whitelist(allow_guest=True)
def headless_setup_account(key):
	"""
	Ignores the data collection step in setup-account.html
	"""
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	frappe.set_user("Administrator")

	create_saas_subscription(account_request)


def create_saas_subscription(account_request):
	team_doc = create_team(account_request)
	site_name = frappe.db.get_value("Site", {"account_request": account_request.name})
	site = frappe.get_doc("Site", site_name)
	site.team = team_doc.name
	site.save()

	subscription = site.subscription
	if subscription:
		subscription.team = team_doc.name
		subscription.save()

	plan = frappe.get_all(
		"Saas App Plan",
		filters={"plan": get_saas_plan(account_request.saas_app)},
		pluck="name",
	)[0]

	frappe.get_doc(
		{
			"doctype": "Saas App Subscription",
			"team": team_doc.name,
			"app": account_request.saas_app,
			"site": site_name,
			"saas_app_plan": plan,
			"initial_plan": json.loads(account_request.url_args).get("plan"),
		}
	).insert(ignore_permissions=True)

	frappe.set_user(team_doc.user)
	frappe.local.login_manager.login_as(team_doc.user)

	return site.name


def create_team(account_request, get_stripe_id=False):
	email = account_request.email

	if not frappe.db.exists("Team", email):
		team_doc = Team.create_new(
			account_request,
			account_request.first_name,
			account_request.last_name,
			password=get_decrypted_password("Account Request", account_request.name, "password"),
			country=account_request.country,
			is_us_eu=account_request.is_us_eu,
			via_erpnext=True,
		)
	else:
		team_doc = frappe.get_doc("Team", email)

	if get_stripe_id:
		return team_doc.stripe_customer_id
	else:
		return team_doc


@frappe.whitelist(allow_guest=True)
def get_site_status(key, app=None):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	domain = get_saas_domain(app) if app else get_erpnext_domain()

	site = frappe.db.get_value(
		"Site",
		{"subdomain": account_request.subdomain, "domain": domain},
		["status", "subdomain"],
		as_dict=1,
	)
	if site:
		return site
	else:
		return {"status": "Pending"}


@frappe.whitelist()
def get_site_url_and_sid(key, app=None):
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


@frappe.whitelist(allow_guest=True)
def login_via_token(token):
	try:
		doc = frappe.get_doc(
			"Saas Remote Login",
			{
				"token": token,
				"status": "Attempted",
				"expires_on": (">", frappe.utils.now()),
			},
		)
		doc.status = "Used"
		frappe.local.login_manager.login_as(doc.team)
		doc.save(ignore_permissions=True)
	except Exception:
		frappe.throw("Token Invalid or Expired!")

	return "success"


# ------------------ Stripe setup ------------------- #
@frappe.whitelist(allow_guest=True)
def setup_intent_success(setup_intent, account_request_key):
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
