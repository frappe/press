# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import time

import boto3
import frappe
import frappe.utils
import pytz
import rq
from botocore.exceptions import ClientError
from frappe.model.document import Document
from oci.core import BlockstorageClient

from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded


class VirtualDiskSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link | None
		duration: DF.Duration | None
		expired: DF.Check
		mariadb_root_password: DF.Password | None
		physical_backup: DF.Check
		progress: DF.Data | None
		region: DF.Link
		rolling_snapshot: DF.Check
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

	def on_update(self):  # noqa: C901
		if self.has_value_changed("status") and self.status == "Unavailable":
			site_backup_name = frappe.db.exists(
				"Site Backup", {"database_snapshot": self.name, "files_availability": ("!=", "Unavailable")}
			)
			if site_backup_name:
				frappe.db.set_value("Site Backup", site_backup_name, "files_availability", "Unavailable")

		if self.has_value_changed("status") and self.status == "Completed":
			old_doc = self.get_doc_before_save()
			if old_doc is None or old_doc.status != "Pending":
				return

			self.duration = frappe.utils.cint(
				frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), self.creation)
			)
			self.save(ignore_version=True)

			if self.physical_backup:
				# Trigger execution of restoration
				physical_restore_name = frappe.db.exists(
					"Physical Backup Restoration", {"disk_snapshot": self.name, "status": "Running"}
				)
				if physical_restore_name:
					frappe.get_doc("Physical Backup Restoration", physical_restore_name).next()

			if self.rolling_snapshot:
				# Find older rolling snapshots than current snapshot
				# If exists, delete that
				older_snapshots = frappe.db.get_all(
					self.doctype,
					{
						"virtual_machine": self.virtual_machine,
						"volume_id": self.volume_id,
						"name": ["!=", self.name],
						"creation": ["<", self.creation],
						"status": ["in", ("Pending", "Completed")],
						"physical_backup": 0,
						"rolling_snapshot": 1,
					},
					pluck="name",
				)
				for older_snapshot_name in older_snapshots:
					frappe.enqueue_doc(
						self.doctype,
						name=older_snapshot_name,
						method="delete_snapshot",
						enqueue_after_commit=True,
						deduplicate=True,
						job_id=f"virtual_disk_snapshot||delete_snapshot||{older_snapshot_name}",
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
		self.save(ignore_version=True)

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

	def create_volume(self, availability_zone: str, iops: int = 3000, throughput: int | None = None) -> str:
		self.sync()
		if self.status != "Completed":
			raise Exception("Snapshot is unavailable")
		if throughput is None:
			throughput = 125
		response = self.client.create_volume(
			SnapshotId=self.snapshot_id,
			AvailabilityZone=availability_zone,
			VolumeType="gp3",
			TagSpecifications=[
				{
					"ResourceType": "volume",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud Snapshot - {self.name}"}],
				},
			],
			Iops=iops,
			Throughput=throughput,
		)
		return response["VolumeId"]

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
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot", {"status": "Pending", "physical_backup": 0, "rolling_snapshot": 0}
	)
	for snapshot in snapshots:
		if has_job_timeout_exceeded():
			return
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot.name).sync()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			return
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Disk Snapshot Sync Error", virtual_snapshot=snapshot.name)


def sync_rolling_snapshots():
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot", {"status": "Pending", "physical_backup": 0, "rolling_snapshot": 1}
	)
	start_time = time.time()
	for snapshot in snapshots:
		if has_job_timeout_exceeded():
			return
		if time.time() - start_time > 600:
			break
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot.name).sync()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			return
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Disk Rolling Snapshot Sync Error", virtual_snapshot=snapshot.name)


def sync_physical_backup_snapshots():
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot",
		{"status": "Pending", "physical_backup": 1, "rolling_snapshot": 0},
		order_by="modified asc",
	)
	start_time = time.time()
	for snapshot in snapshots:
		if has_job_timeout_exceeded():
			return
		# if already spent more than 1 minute, then don't do sync anymore
		# because this function will be executed every minute
		# we don't want to run two syncs at the same time
		if time.time() - start_time > 60:
			break
		try:
			frappe.get_doc("Virtual Disk Snapshot", snapshot.name).sync()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			return
		except Exception:
			frappe.db.rollback()
			log_error(
				title="Physical Restore : Virtual Disk Snapshot Sync Error", virtual_snapshot=snapshot.name
			)


def delete_old_snapshots():
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot",
		{
			"status": "Completed",
			"creation": ("<=", frappe.utils.add_days(None, -2)),
			"physical_backup": False,
			"rolling_snapshot": False,
		},
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


def delete_expired_snapshots():
	snapshots = frappe.get_all(
		"Virtual Disk Snapshot",
		filters={"status": "Completed", "physical": True, "rolling_snapshot": False, "expired": True},
		pluck="name",
		order_by="creation asc",
		limit=500,
	)
	for snapshot in snapshots:
		try:
			# Ensure there is no Restoration which is using / can use this snapshot
			if (
				frappe.db.count(
					"Physical Backup Restoration",
					filters={
						"disk_snapshot": snapshot,
						"status": ["in", ["Pending", "Scheduled", "Running"]],
					},
				)
				> 0
			) or (
				frappe.db.count(
					"Physical Backup Restoration",
					filters={
						"disk_snapshot": snapshot,
						"is_failure_resolved": False,
						"status": "Failure",
					},
				)
				> 0
			):
				continue

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
