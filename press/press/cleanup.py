import datetime
import frappe
from frappe.desk.form.load import get_attachments


def remove_baggage():
	# condition: any sort of file attached to a site and creation time > 24 hr
	past_day = datetime.date.today() - datetime.timedelta(days=1)
	or_filters = [
		["database_file", "!=", ""],
		["public_file", "!=", ""],
		["private_file", "!=", ""],
		["remote_database_file", "!=", ""],
		["remote_public_file", "!=", ""],
		["remote_private_file", "!=", ""],
	]
	filters = [
		["creation", "<", past_day],
		["status", "not in", "Pending,Installing,Updating,Active,Broken"]
	]

	sites = frappe.get_all("Site", filters=filters, or_filters=or_filters)

	for site in sites:
		# remove local files attached to site
		attachments = get_attachments("Site", site["name"])
		for attachment in attachments:
			frappe.get_doc("File", attachment["name"]).delete()

		# remove remote files attached to site
		remote_files = frappe.db.get_value("Site", site["name"], [
			"remote_database_file",
			"remote_public_file",
			"remote_private_file"
		])
		for remote_file in remote_files:
			# this only deletes the object from s3, link still exists
			frappe.get_doc("Remote File", remote_file).delete_remote_object()

