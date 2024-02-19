import frappe


def execute():
	plans = frappe.get_all(
		"Site Plan",
		{
			"document_type": (
				"in",
				["Server", "Database Server", "Proxy Server", "Self Hosted Server"],
			)
		},
		pluck="name",
	)

	for plan in plans:
		plan_doc = frappe.get_doc("Site Plan", plan)
		server_plan_doc = frappe.get_doc(
			{
				"doctype": "Server Plan",
				"name": plan_doc.name,
				"title": plan_doc.plan_title,
				"price_inr": plan_doc.price_inr,
				"price_usd": plan_doc.price_usd,
				"server_type": plan_doc.document_type,
				"cluster": plan_doc.cluster,
				"instance_type": plan_doc.instance_type,
				"vcpu": plan_doc.vcpu,
				"memory": plan_doc.memory,
				"disk": plan_doc.disk,
				"enabled": plan_doc.enabled,
			}
		)
		server_plan_doc.roles = plan_doc.roles
		server_plan_doc.insert(ignore_if_duplicate=True)

	for marketplace_plan in frappe.get_all("Marketplace App Plan", pluck="name"):
		map_doc = frappe.get_doc("Marketplace App Plan", marketplace_plan)
		plan = frappe.get_all(
			"Plan", {"name": map_doc.plan}, ["plan_title", "price_usd", "price_inr"]
		)

		if plan:
			plan = plan[0]
		else:
			continue

		map_doc.title = plan.plan_title
		map_doc.price_inr = plan.price_inr
		map_doc.price_usd = plan.price_usd
		map_doc.save()
