import frappe


def execute():
	# site plans
	site_plans = frappe.get_all("Plan", {"document_type": "Site"}, pluck="name")
	for site_plan in site_plans:
		plan = frappe.get_doc("Plan", site_plan)
		attrs = [
			{"name": "cpu_time_per_day", "type": "Int", "value": plan.cpu_time_per_day},
			{"name": "max_database_usage", "type": "Int", "value": plan.max_database_usage},
			{"name": "max_storage_usage", "type": "Int", "value": plan.max_storage_usage},
			{"name": "is_trial_plan", "type": "Check", "value": plan.is_trial_plan},
			{"name": "offsite_backups", "type": "Check", "value": plan.offsite_backups},
			{"name": "private_benches", "type": "Check", "value": plan.private_benches},
			{"name": "database_access", "type": "Check", "value": plan.database_access},
			{"name": "monitor_access", "type": "Check", "value": plan.monitor_access},
			{
				"name": "dedicated_server_plan",
				"type": "Check",
				"value": plan.dedicated_server_plan,
			},
			{"name": "is_frappe_plan", "type": "Check", "value": plan.is_frappe_plan},
		]
		plan.attributes = []
		for attr in attrs:
			plan.append(
				"attributes",
				{"fieldname": attr["name"], "fieldtype": attr["type"], "value": attr["value"]},
			)

		plan.save(ignore_permissions=True)

	# server plans
	server_plans = frappe.get_all(
		"Plan", {"document_type": ("in", ["Server", "Database Server"])}, pluck="name"
	)
	for server_plan in server_plans:
		plan = frappe.get_doc("Plan", server_plan)
		attrs = [
			{"name": "vcpu", "type": "Int", "value": plan.vcpu},
			{"name": "memory", "type": "Int", "value": plan.memory},
			{"name": "disk", "type": "Int", "value": plan.disk},
			{"name": "cluster", "type": "Link", "value": plan.cluster},
			{"name": "instance_type", "type": "Data", "value": plan.instance_type},
		]
		plan.attributes = []
		for attr in attrs:
			plan.append(
				"attributes",
				{"fieldname": attr["name"], "fieldtype": attr["type"], "value": attr["value"]},
			)

		plan.save(ignore_permissions=True)

	# marketplace plans
	marketplace_plans = frappe.get_all("Marketplace App Plan", fields=["name", "plan"])
	for marketplace_plan in marketplace_plans:
		versions = frappe.get_all(
			"App Plan Version", {"parent": marketplace_plan["name"]}, pluck="version"
		)
		features = frappe.get_all(
			"Plan Feature", {"parent": marketplace_plan["name"]}, pluck="description"
		)

		plan = frappe.get_doc("Plan", marketplace_plan["plan"])
		plan.attributes = []

		for version in versions:
			plan.append(
				"attributes", {"fieldname": "version", "fieldtype": "Data", "value": version}
			)
		for feature in features:
			plan.append(
				"attributes", {"fieldname": "feature", "fieldtype": "Data", "value": feature}
			)

		plan.append(
			"attributes",
			{"fieldname": "is_trial_plan", "fieldtype": "Check", "value": plan.is_trial_plan},
		)

		plan.save(ignore_permissions=True)

	frappe.db.commit()
