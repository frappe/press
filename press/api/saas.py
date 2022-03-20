import frappe


@frappe.whitelist()
def get_apps():

	return [{}]


@frappe.whitelist()
def get_plans():
	app = "storage_integration"
	saas_app = frappe.get_doc("Saas App", app)
	plans = saas_app.get_plans()

	return plans
