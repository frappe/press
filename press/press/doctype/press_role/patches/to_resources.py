import frappe


def execute():
	maps = {
		"site": "Site",
		"server": "Server",
		"release_group": "Release Group",
	}

	for permission in frappe.get_all("Press Role Permission", fields=["role", *maps.keys()]):
		role = frappe.get_doc("Press Role", permission.role)
		to_append = filter(
			lambda x: x.get("document_name"),
			map(
				lambda key: {
					"document_type": maps[key],
					"document_name": permission[key],
				},
				maps.keys(),
			),
		)

		for item in to_append:
			role.append("resources", item)

		role.save()
		frappe.db.commit()
