from datetime import datetime, timedelta
import frappe
from frappe.desk.form.load import get_attachments
from frappe.utils.password import get_decrypted_password
import json
from boto3 import client


def remove_baggage():
	# condition: any sort of file attached to a site and creation time > 12 hr
	half_day = datetime.datetime.now() - datetime.timedelta(hours=12)
	or_filters = [
		["database_file", "!=", ""],
		["public_file", "!=", ""],
		["private_file", "!=", ""],
		["remote_database_file", "!=", ""],
		["remote_public_file", "!=", ""],
		["remote_private_file", "!=", ""],
	]
	filters = [
		["creation", "<", half_day],
		["status", "not in", "Pending,Installing,Updating,Active,Broken"],
	]

	sites = frappe.get_all("Site", filters=filters, or_filters=or_filters)

	for site in sites:
		# remove local files attached to site
		attachments = get_attachments("Site", site["name"])
		for attachment in attachments:
			frappe.delete_doc_if_exists("File", attachment["name"])

		# remove remote files attached to site
		remote_files = frappe.db.get_value(
			"Site",
			site["name"],
			["remote_database_file", "remote_public_file", "remote_private_file"],
		)
		for remote_file in remote_files:
			# this only deletes the object from s3, link still exists
			frappe.get_doc("Remote File", remote_file).delete_remote_object()


def cleanup_offsite_backups():
	sites = frappe.get_all("Site")
	keep_count = frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30

	for site in sites:
		expired_offsite_backups = frappe.get_all("Site Backup", filters={"site": site["name"], "offsite": 1, "status": "Success"}, order_by="creation desc", limit_start=keep_count, limit_page_length=keep_count)

		for offsite_backup in expired_offsite_backups:
			site_backup = frappe.get_doc("Site Backup", offsite_backup["name"])
			offsite_data = json.loads(site_backup.offsite_backup)

			for remote_file in offsite_data.values():
				s3_client = client("s3",
					aws_access_key_id=frappe.db.get_single_value("Press Settings", "offsite_backups_access_key_id"),
					aws_secret_access_key=get_decrypted_password("Press Settings", "Press Settings", "offsite_backups_secret_access_key"),
					region_name="ap-south-1",
				)
				s3_client.delete_object(
					Bucket=frappe.db.get_single_value("Press Settings", "aws_s3_bucket"),
					Key=remote_file,
				)
