import frappe


def execute():
	"""
	From the app release, get the app source and add it to the app audit.
	"""

	marketplace_app_audit = frappe.qb.DocType("Marketplace App Audit")
	app_release = frappe.qb.DocType("App Release")
	# Fetch each Marketplace App Audit and its corresponding App Release's source,
	# then update each Marketplace App Audit document with the correct app_source.

	# get list of audit name <-> app_release.source pairs to update
	audits_with_sources = (
		frappe.qb.from_(marketplace_app_audit)
		.join(app_release)
		.on(marketplace_app_audit.app_release == app_release.name)
		.select(marketplace_app_audit.name, app_release.source)
		.run(as_dict=True)
	)

	for row in audits_with_sources:
		# update individually to set app_source per audit row
		frappe.db.set_value("Marketplace App Audit", row.get("name"), "app_source", row.get("source"))
