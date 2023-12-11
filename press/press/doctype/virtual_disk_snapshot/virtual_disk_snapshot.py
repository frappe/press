# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import boto3
from press.utils import log_error


class VirtualDiskSnapshot(Document):
	def before_insert(self):
		self.set_credentials()

	def after_insert(self):
		self.sync()

	def set_credentials(self):
		series = frappe.db.get_value("Virtual Machine", self.virtual_machine, "series")
		if series == "m" and frappe.db.exists("Database Server", self.virtual_machine):
			self.mariadb_root_password = frappe.get_doc(
				"Database Server", self.virtual_machine
			).get_password("mariadb_root_password")

	@frappe.whitelist()
	def sync(self):
		try:
			snapshots = self.client.describe_snapshots(SnapshotIds=[self.snapshot_id])[
				"Snapshots"
			]
			if snapshots:
				snapshot = snapshots[0]
				self.aws_volume_id = snapshot["VolumeId"]
				self.snapshot_id = snapshot["SnapshotId"]

				self.status = self.get_status_map(snapshot["State"])
				self.description = snapshot["Description"]
				self.size = snapshot["VolumeSize"]
				self.start_time = frappe.utils.format_datetime(
					snapshot["StartTime"], "yyyy-MM-dd HH:mm:ss"
				)
				self.progress = snapshot["Progress"]
		except Exception:
			self.status = "Unavailable"
		self.save()

	@frappe.whitelist()
	def delete_snapshot(self):
		self.sync()
		if self.status == "Unavailable":
			return
		self.client.delete_snapshot(SnapshotId=self.snapshot_id)
		self.sync()

	def get_status_map(self, status):
		return {
			"pending": "Pending",
			"completed": "Completed",
			"error": "Error",
			"recovering": "Recovering",
			"recoverable": "Recoverable",
		}.get(status, "Unavailable")

	@property
	def client(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		return boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)


def sync_snapshots():
	snapshots = frappe.get_all("Virtual Disk Snapshot", {"status": "Pending"})
	for snapshot in snapshots:
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot.name).sync()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Disk Snapshot Sync Error", virtual_snapshot=snapshot.name)


def delete_old_snapshots():
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot",
		{"status": "Completed", "creation": ("<=", frappe.utils.add_days(None, -2))},
		pluck="name",
		order_by="creation asc",
		limit=50,
	)
	for snapshot in snapshots:
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot).delete_snapshot()
			frappe.db.commit()
		except Exception:
			log_error("Virtual Disk Snapshot Delete Error", snapshot=snapshot)
			frappe.db.rollback()
