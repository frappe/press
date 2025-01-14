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
		"Site", fields=["name", *fields], filters=filters, or_filters=or_filters, pluck="name"
	)

	# s3 uploads.frappe.cloud has a 1 day expiry rule for all objects, so we'll unset those files here
	for remote_file_type in fields:
		frappe.db.set_value("Site", {"name": ("in", sites)}, remote_file_type, None)


def reset_large_output_fields_from_ansible_tasks():
	# These ansible tasks can create very large output
	# Cause table bloat, backup failure etc
	# The output of these tasks isn't all that useful after some time
	TASKS = [
		"Move Backup Directory to MariaDB Data Directory",
		"Prepare MariaBackup",
		"RSync Backup Directory From Primary",
		"Run MariaDB Upgrade",
		"Run migrate on site",
		"Start MariaBackup",
	]

	tasks = frappe.get_all(
		"Ansible Task", {"task": ("in", TASKS), "creation": ("<=", frappe.utils.add_days(None, -2))}, ["name"]
	)
	for task in tasks:
		frappe.db.set_value(
			"Ansible Task", task.name, {"output": "", "result": "", "exception": "", "error": ""}
		)
		frappe.db.commit()
