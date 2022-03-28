import frappe
from press.utils import get_current_team


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
