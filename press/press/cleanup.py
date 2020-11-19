from datetime import datetime, timedelta

import frappe
from frappe.desk.form.load import get_attachments


def remove_baggage():
	# condition: any sort of file attached to a site and creation time > 12 hr
	half_day = datetime.now() - timedelta(hours=12)
	or_filters = [
		["database_file", "!=", ""],
		["public_file", "!=", ""],
		["private_file", "!=", ""],
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
		"Site", fields=["name"] + fields, filters=filters, or_filters=or_filters
	)

	for site in sites:
		# remove local files attached to site
		attachments = get_attachments("Site", site.name)
		for attachment in attachments:
			frappe.delete_doc_if_exists("File", attachment["name"])

		# remove remote files attached to site
		remote_files = {x: site.get(x) for x in fields}

		for remote_file_type, remote_file_name in remote_files.items():
			# s3 uploads.frappe.cloud has a 1 day expiry rule for all objects, so we'll let it handle that
			frappe.db.set_value("Site", site.name, remote_file_type, None, for_update=False)


def cleanup_offsite_backups():
	from press.utils import chunk
	from frappe.utils.password import get_decrypted_password
	from boto3 import resource

	backups_bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")
	if not backups_bucket:
		return

	s3_objects = {}
	files_to_drop = []
	offsite_bucket = {
		"bucket": backups_bucket,
		"access_key_id": frappe.db.get_single_value(
			"Press Settings", "offsite_backups_access_key_id"
		),
		"secret_access_key": get_decrypted_password(
			"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
		),
	}
	s3 = resource(
		"s3",
		aws_access_key_id=offsite_bucket["access_key_id"],
		aws_secret_access_key=offsite_bucket["secret_access_key"],
		region_name="ap-south-1",
	)
	sites = frappe.get_all("Site", filters={"status": ("!=", "Archived")}, pluck="name")
	keep_count = (
		frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
	)

	for i, site in enumerate(sites):
		expired_offsite_backups = frappe.get_all(
			"Site Backup",
			filters={
				"site": site,
				"status": "Success",
				"backup_availability": "Available",
				"offsite": True,
			},
			order_by="creation desc",
		)[keep_count:]

		for offsite_backup in expired_offsite_backups:
			remote_files = frappe.db.get_value(
				"Site Backup",
				offsite_backup["name"],
				["remote_database_file", "remote_private_file", "remote_public_file"],
			)
			files_to_drop.extend(remote_files)

	for remote_file in set(files_to_drop):
		if remote_file:
			s3_objects[remote_file] = frappe.db.get_value(
				"Remote File", remote_file, "file_path"
			)

	if not s3_objects:
		return

	for objects in chunk([{"Key": x} for x in s3_objects.values()], 1000):
		s3.Bucket(offsite_bucket["bucket"]).delete_objects(Delete={"Objects": objects})

	for key in s3_objects:
		frappe.db.set_value("Remote File", key, "status", "Unavailable")

	frappe.db.commit()


def remove_logs():
	for doctype in (
		"Site Uptime Log",
		"Site Request Log",
		"Site Job Log",
	):
		frappe.db.delete(doctype, {"modified": ("<", datetime.now() - timedelta(days=10))})
		frappe.db.commit()

	frappe.db.delete(doctype, {"modified": ("<", datetime.now() - timedelta(days=1))})
	frappe.db.commit()
