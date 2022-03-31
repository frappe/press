import json
import frappe
from frappe.core.utils import find
from press.utils import get_current_team

# from press.utils.billing import get_erpnext_com_connection
from press.press.doctype.site.saas_site import SaasSite, get_saas_domain
from press.press.doctype.site.saas_pool import get as get_pooled_saas_site


@frappe.whitelist()
def get_saas_subscriptions_for_team():
	"""Used in App Switcher"""
	team = get_current_team()

	subscriptions = frappe.get_all(
		"Saas App Subscription",
		filters={"team": team, "status": ("!=", "Disabled")},
		fields=["name", "plan", "site", "app", "app_name"],
	)

	return subscriptions


@frappe.whitelist()
def get_plans(site):
	# TODO: set this while login to dashboard or some other way
	app = "storage_integration"
	saas_app = frappe.get_doc("Saas App", app)
	plans = saas_app.get_plans(site)

	return plans


@frappe.whitelist()
def change_app_plan(site, app, new_plan):
	subscription_name = frappe.get_all(
		"Saas App Subscription",
		filters={"site": site, "app": app["app"], "status": ("!=", "Disabled")},
		pluck="name",
	)
	subscription = frappe.get_doc("Saas App Subscription", subscription_name[0])
	subscription.saas_app_plan = new_plan["name"]
	subscription.save(ignore_permissions=True)


# ----------------------------- SIGNUP APIs ---------------------------------


@frappe.whitelist(allow_guest=True)
def account_request(
	subdomain, email, first_name, last_name, phone_number, country, url_args=None
):
	app = json.loads(url_args)["app"]
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
			"erpnext": True,
			"subdomain": subdomain,
			"email": email,
			"role": "Press Admin",
			"first_name": first_name,
			"last_name": last_name,
			"phone_number": phone_number,
			"country": country,
			"url_args": url_args,
		}
	).insert(ignore_permissions=True)

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
			SaasSite(account_request=account_request, app=app).insert(ignore_permissions=True)
	finally:
		frappe.set_user(current_user)
		frappe.session.data = current_session_data


@frappe.whitelist(allow_guest=True)
def check_subdomain_availability(subdomain, app):
	# Only for ERPNext domains

	# erpnext_com = get_erpnext_com_connection()
	# result = erpnext_com.post_api(
	# 	"central.www.signup.check_subdomain_availability", {"subdomain": subdomain}
	# )
	# if result:
	# 	return False

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
