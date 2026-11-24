import frappe


def execute():
	"""Name the Press Settings bucket on clusters without one, so the mandatory field moves no backups."""
	bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")
	if not bucket:
		return

	if not frappe.db.exists("Backup Bucket", bucket):
		region = frappe.db.get_single_value("Press Settings", "backup_region")
		frappe.get_doc({"doctype": "Backup Bucket", "bucket_name": bucket, "region": region}).insert(
			ignore_permissions=True
		)

	frappe.db.set_value(
		"Cluster", {"backup_bucket": ("is", "not set")}, "backup_bucket", bucket, update_modified=False
	)
