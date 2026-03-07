import frappe


def execute():
	enabled_site_plans = frappe.db.get_all(
		"Site Plan",
		filters={"enabled": 1, "document_type": "Site"},
		pluck="name",
	)

	provider_names = (
		frappe.db.get_all(
			"Cloud Provider",
			pluck="name",
		)
		or []
	)

	if not (enabled_site_plans and provider_names):
		return

	for plan_name in enabled_site_plans:
		plan = frappe.get_doc("Site Plan", plan_name)
		for provider in provider_names:
			plan.append("cloud_providers", {"cloud_provider": provider})

		plan.save()

	frappe.db.commit()
