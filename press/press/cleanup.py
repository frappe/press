import frappe


def unlink_remote_files_from_site():
	"""Remove any remote files attached to the Site doc if older than 12 hours."""
	half_day = frappe.utils.add_to_date(None, hours=-12)
	or_filters = [
		["remote_config_file", "!=", ""],
		["remote_database_file", "!=", ""],
		["remote_public_file", "!=", ""],
		["remote_private_file", "!=", ""],
	]
	filters = [
		["creation", "<", half_day],
		["status", "not in", "Pending,Installing,Updating,Active,Broken"],
	]
	fields = [
		"remote_config_file",
		"remote_database_file",
		"remote_public_file",
		"remote_private_file",
	]
	sites = frappe.get_all(
		"Site", fields=["name"] + fields, filters=filters, or_filters=or_filters, pluck="name"
	)

	# s3 uploads.frappe.cloud has a 1 day expiry rule for all objects, so we'll unset those files here
	for remote_file_type in fields:
		frappe.db.set_value("Site", {"name": ("in", sites)}, remote_file_type, None)
