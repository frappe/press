# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import boto3
import frappe
import pytz
from botocore.exceptions import ClientError
from frappe.model.document import Document
from oci.core import BlockstorageClient

from press.utils import log_error


class VirtualDiskSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link | None
		mariadb_root_password: DF.Password | None
		progress: DF.Data | None
		region: DF.Link
		size: DF.Int
		snapshot_id: DF.Data
		start_time: DF.Datetime | None
		status: DF.Literal["Pending", "Completed", "Error", "Recovering", "Recoverable", "Unavailable"]
		virtual_machine: DF.Link
		volume_id: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		self.set_credentials()

	def after_insert(self):
		self.sync()

	def set_credentials(self):
		series = frappe.db.get_value("Virtual Machine", self.virtual_machine, "series")
		if series == "m" and frappe.db.exists("Database Server", self.virtual_machine):
			self.mariadb_root_password = frappe.get_doc("Database Server", self.virtual_machine).get_password(
				"mariadb_root_password"
			)

	@frappe.whitelist()
	def sync(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			try:
				snapshots = self.client.describe_snapshots(SnapshotIds=[self.snapshot_id])["Snapshots"]
				if snapshots:
					snapshot = snapshots[0]
					self.volume_id = snapshot["VolumeId"]
					self.snapshot_id = snapshot["SnapshotId"]

					self.status = self.get_aws_status_map(snapshot["State"])
					self.description = snapshot["Description"]
					self.size = snapshot["VolumeSize"]
					self.start_time = frappe.utils.format_datetime(
						snapshot["StartTime"], "yyyy-MM-dd HH:mm:ss"
					)
					self.progress = snapshot["Progress"]
			except Exception:
				self.status = "Unavailable"
		elif cluster.cloud_provider == "OCI":
			if ".bootvolumebackup." in self.snapshot_id:
				snapshot = self.client.get_boot_volume_backup(self.snapshot_id).data
				self.volume_id = snapshot.boot_volume_id
			else:
				snapshot = self.client.get_volume_backup(self.snapshot_id).data
				self.volume_id = snapshot.volume_id
			self.status = self.get_oci_status_map(snapshot.lifecycle_state)
			self.description = snapshot.display_name
			self.size = snapshot.size_in_gbs

			self.start_time = frappe.utils.format_datetime(
				snapshot.time_created.astimezone(pytz.timezone(frappe.utils.get_system_timezone())),
				"yyyy-MM-dd HH:mm:ss",
			)
		self.save()

	@frappe.whitelist()
	def delete_snapshot(self):
		self.sync()
		if self.status == "Unavailable":
			return
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			try:
				self.client.delete_snapshot(SnapshotId=self.snapshot_id)
			except ClientError as e:
				if e.response["Error"]["Code"] == "InvalidSnapshot.InUse":
					frappe.msgprint("Snapshot is in use", alert=True)
				else:
					raise e
		elif cluster.cloud_provider == "OCI":
			if ".bootvolumebackup." in self.snapshot_id:
				self.client.delete_boot_volume_backup(self.snapshot_id)
			else:
				self.client.delete_volume_backup(self.snapshot_id)
		self.sync()

	def get_aws_status_map(self, status):
		return {
			"pending": "Pending",
			"completed": "Completed",
			"error": "Error",
			"recovering": "Recovering",
			"recoverable": "Recoverable",
		}.get(status, "Unavailable")

	def get_oci_status_map(self, status):
		return {
			"CREATING": "Pending",
			"AVAILABLE": "Completed",
			"TERMINATING": "Pending",
			"TERMINATED": "Unavailable",
			"FAULTY": "Error",
			"REQUEST_RECEIVED": "Pending",
		}.get(status, "Unavailable")

	@property
	def client(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			return boto3.client(
				"ec2",
				region_name=self.region,
				aws_access_key_id=cluster.aws_access_key_id,
				aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
			)
		if cluster.cloud_provider == "OCI":
			return BlockstorageClient(cluster.get_oci_config())
		return None


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
		limit=500,
	)
	for snapshot in snapshots:
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot).delete_snapshot()
			frappe.db.commit()
		except Exception:
			log_error("Virtual Disk Snapshot Delete Error", snapshot=snapshot)
			frappe.db.rollback()


def sync_all_snapshots_from_aws():
	regions = frappe.get_all("Cloud Region", {"provider": "AWS EC2"}, pluck="name")
	for region in regions:
		if not frappe.db.exists("Virtual Disk Snapshot", {"region": region}):
			continue
		random_snapshot = frappe.get_doc(
			"Virtual Disk Snapshot",
			{
				"region": region,
			},
		)
		client = random_snapshot.client
		paginator = client.get_paginator("describe_snapshots")
		for page in paginator.paginate(OwnerIds=["self"], Filters=[{"Name": "tag-key", "Values": ["Name"]}]):
			for snapshot in page["Snapshots"]:
				if _should_skip_snapshot(snapshot):
					continue
				try:
					delete_duplicate_snapshot_docs(snapshot)
					if _update_snapshot_if_exists(snapshot, random_snapshot):
						continue
					tag_name = next(tag["Value"] for tag in snapshot["Tags"] if tag["Key"] == "Name")
					virtual_machine = tag_name.split(" - ")[1]
					_insert_snapshot(snapshot, virtual_machine, random_snapshot)
					frappe.db.commit()
				except Exception:
					log_error(
						title="Virtual Disk Snapshot Sync Error",
						snapshot=snapshot,
					)
					frappe.db.rollback()


def _insert_snapshot(snapshot, virtual_machine, random_snapshot):
	start_time = frappe.utils.format_datetime(snapshot["StartTime"], "yyyy-MM-dd HH:mm:ss")
	new_snapshot = frappe.get_doc(
		{
			"doctype": "Virtual Disk Snapshot",
			"snapshot_id": snapshot["SnapshotId"],
			"virtual_machine": virtual_machine,
			"volume_id": snapshot["VolumeId"],
			"status": random_snapshot.get_aws_status_map(snapshot["State"]),
			"description": snapshot["Description"],
			"size": snapshot["VolumeSize"],
			"start_time": start_time,
			"progress": snapshot["Progress"],
		}
	).insert()
	frappe.db.set_value(
		"Virtual Disk Snapshot",
		new_snapshot.name,
		{"creation": start_time, "modified": start_time},
		update_modified=False,
	)
	return new_snapshot


def _should_skip_snapshot(snapshot):
	tag_names = [tag["Value"] for tag in snapshot["Tags"] if tag["Key"] == "Name"]
	if not tag_names:
		return True
	tag_name_parts = tag_names[0].split(" - ")
	if len(tag_name_parts) != 3:
		return True
	identifier, virtual_machine, _ = tag_name_parts
	if identifier != "Frappe Cloud":
		return True
	if not frappe.db.exists("Virtual Machine", virtual_machine):
		return True

	return False


def delete_duplicate_snapshot_docs(snapshot):
	# Delete all except one snapshot document
	# It doesn't matter which one we keep
	snapshot_id = snapshot["SnapshotId"]
	snapshot_count = frappe.db.count("Virtual Disk Snapshot", {"snapshot_id": snapshot_id})
	if snapshot_count > 1:
		frappe.db.sql(
			"""
				DELETE
				FROM `tabVirtual Disk Snapshot`
				WHERE snapshot_id=%s
				LIMIT %s
			""",
			(snapshot_id, snapshot_count - 1),
		)


def _update_snapshot_if_exists(snapshot, random_snapshot):
	snapshot_id = snapshot["SnapshotId"]
	if frappe.db.exists("Virtual Disk Snapshot", {"snapshot_id": snapshot_id}):
		frappe.db.set_value(
			"Virtual Disk Snapshot",
			{"snapshot_id": snapshot_id},
			"status",
			random_snapshot.get_aws_status_map(snapshot["State"]),
		)
		return True
	return False
