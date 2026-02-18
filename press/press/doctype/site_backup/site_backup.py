# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import json
import time
from typing import TYPE_CHECKING

import frappe
import frappe.utils
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document

from press.agent import Agent
from press.exceptions import SiteTooManyPendingBackups
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from datetime import date

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.site_update.site_update import SiteUpdate
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

ARCHIVED_SITE_BACKUP_RETENTION_CUTOFF_DATE = frappe.utils.add_to_date(frappe.utils.now(), months=-6)


class SiteBackup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		config_file: DF.Data | None
		config_file_size: DF.Data | None
		config_file_url: DF.Text | None
		database_file: DF.Data | None
		database_name: DF.Data | None
		database_size: DF.Data | None
		database_snapshot: DF.Link | None
		database_url: DF.Text | None
		deactivate_site_during_backup: DF.Check
		files_availability: DF.Literal["", "Available", "Unavailable"]
		for_site_update: DF.Check
		job: DF.Link | None
		offsite: DF.Check
		offsite_backup: DF.Code | None
		physical: DF.Check
		private_file: DF.Data | None
		private_size: DF.Data | None
		private_url: DF.Text | None
		public_file: DF.Data | None
		public_size: DF.Data | None
		public_url: DF.Text | None
		remote_config_file: DF.Link | None
		remote_database_file: DF.Link | None
		remote_private_file: DF.Link | None
		remote_public_file: DF.Link | None
		site: DF.Link
		snapshot_request_key: DF.Data | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		team: DF.Link | None
		with_files: DF.Check
	# end: auto-generated types

	dashboard_fields = (
		"job",
		"status",
		"database_url",
		"public_url",
		"private_url",
		"config_file_url",
		"site",
		"database_size",
		"public_size",
		"private_size",
		"with_files",
		"offsite",
		"files_availability",
		"remote_database_file",
		"remote_public_file",
		"remote_private_file",
		"remote_config_file",
		"physical",
		"database_snapshot",
	)

	@property
	def database_server(self):
		return frappe.get_value("Server", self.server, "database_server")

	@property
	def server(self):
		return frappe.get_cached_value("Site", self.site, "server")

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		"""
		Remove records with `Success` but files_availability is `Unavailable`
		"""
		sb = frappe.qb.DocType("Site Backup")
		query = query.where(~((sb.files_availability == "Unavailable") & (sb.status == "Success")))
		if filters.get("backup_date"):
			with contextlib.suppress(Exception):
				date = frappe.utils.getdate(filters["backup_date"])
				query = query.where(
					sb.creation.between(
						frappe.utils.add_to_date(date, hours=0, minutes=0, seconds=0),
						frappe.utils.add_to_date(date, hours=23, minutes=59, seconds=59),
					)
				)

		if not filters.get("status"):
			query = query.where(sb.status == "Success")

		results = [
			result
			for result in query.run(as_dict=True)
			if not (result.get("physical") and result.get("for_site_update"))
		]

		return [
			{
				**result,
				"type": "Physical" if result.get("physical") else "Logical",
				"ready_to_restore": True
				if result.get("physical") == 0
				else frappe.get_cached_value(
					"Virtual Disk Snapshot", result.get("database_snapshot"), "status"
				)
				== "Completed",
			}
			for result in results
		]

	def validate(self):
		if self.physical and self.with_files:
			frappe.throw("Physical backups cannot be taken with files")
		if self.physical and self.offsite:
			frappe.throw("Physical and offsite logical backups cannot be taken together")

		if self.deactivate_site_during_backup and not self.physical:
			frappe.throw("Site deactivation should be used for physical backups only")

	def before_insert(self):
		if self.flags.get("skip_backup_after_insert"):
			return

		if getattr(self, "force", False):
			if self.physical:
				frappe.throw("Physical backups cannot be forcefully triggered")
			return

		# For backups, check if there are too many pending backups
		two_hours_ago = frappe.utils.add_to_date(None, hours=-2)
		if frappe.db.count(
			"Site Backup",
			{
				"site": self.site,
				"status": ("in", ["Running", "Pending"]),
				"creation": (">", two_hours_ago),
			},
		):
			frappe.throw("Too many pending backups", SiteTooManyPendingBackups)

		self.validate_and_setup_physical_backup()

	def after_insert(self):
		# Skip backup creation if this record was created from archive site or unistall app jobs (backup already performed, just recording it)
		if self.flags.get("skip_backup_after_insert"):
			return

		if self.deactivate_site_during_backup:
			agent = Agent(self.server)
			agent.deactivate_site(
				frappe.get_doc("Site", self.site), reference_doctype=self.doctype, reference_name=self.name
			)
		else:
			self.start_backup()

	def validate_and_setup_physical_backup(self):
		if not self.physical:
			return
		# Validate physical backup enabled on database server
		if not bool(
			frappe.utils.cint(
				frappe.get_value("Database Server", self.database_server, "enable_physical_backup")
			)
		):
			frappe.throw(
				"Physical backup is not enabled for this database server. Please reach out to support."
			)
		# Set some default values
		site = frappe.get_doc("Site", self.site)
		if not site.database_name:
			site.sync_info()
			site.reload()
		if not site.database_name:
			frappe.throw("Database name is missing in the site")
		self.database_name = site.database_name
		self.snapshot_request_key = frappe.generate_hash(length=32)

	def start_backup(self):
		if self.physical:
			frappe.enqueue_doc(
				doctype=self.doctype,
				name=self.name,
				method="_create_physical_backup",
				enqueue_after_commit=True,
			)
		else:
			site = frappe.get_doc("Site", self.site)
			agent = Agent(site.server)
			job = agent.backup_site(site, self)
			frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def after_delete(self):
		if self.job:
			frappe.delete_doc_if_exists("Agent Job", self.job)

	def on_update(self):  # noqa: C901
		if self.physical and self.has_value_changed("status") and self.status in ["Success", "Failure"]:
			site_update_doc_name = frappe.db.exists("Site Update", {"site_backup": self.name})
			if site_update_doc_name:
				"""
				If site backup was trigerred for Site Update,
				Then, trigger Site Update to proceed with the next steps
				"""
				site_update: SiteUpdate = frappe.get_doc("Site Update", site_update_doc_name)
				if self.status == "Success":
					site_update.create_update_site_agent_request()
				elif self.status == "Failure":
					site_update.activate_site(backup_failed=True)

			frappe.enqueue_doc(
				self.doctype,
				self.name,
				method="_rollback_db_directory_permissions",
				enqueue_after_commit=True,
			)

		if (
			self.has_value_changed("status")
			and self.status in ["Success", "Failure"]
			and self.deactivate_site_during_backup
		):
			agent = Agent(self.server)
			agent.activate_site(
				frappe.get_doc("Site", self.site), reference_doctype=self.doctype, reference_name=self.name
			)

		try:
			if (
				not self.physical
				and self.has_value_changed("status")
				and frappe.db.get_value("Agent Job", self.job, "status") == "Failure"
			):
				self.autocorrect_bench_permissions()
		except Exception:
			frappe.log_error(
				"Failed to correct bench permissions",
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

		if (
			not self.physical
			and self.has_value_changed("status")
			and frappe.db.get_value("Agent Job", self.job, "status") == "Failure"
		):
			self.fix_global_search_indexes()

	def _rollback_db_directory_permissions(self):
		if not self.physical:
			return
		"""
		Rollback the permission changes made to the database directory
		Change it back to 770 from 700

		Check `_create_physical_backup` method for more information
		"""
		success = self.run_ansible_command_in_database_server(
			f"chmod 700 /var/lib/mysql/{self.database_name}"
		)
		if not success:
			"""
			Don't throw an error here, Because the backup is already created
			And keeping the permission as 770 will not cause issue in database operations
			"""
			frappe.log_error(
				"Failed to rollback the permission changes of the database directory",
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def _create_physical_backup(self):
		site = frappe.get_doc("Site", self.site)
		"""
		Change the /var/lib/mysql/<database_name> directory's permission to 700 from 770
		The files inside that directory will have 660 permission, So no need to change the permission of the files

		`frappe` user on server is already part of `mysql` group.
		So `frappe` user can read-write the files inside that directory
		"""
		success = self.run_ansible_command_in_database_server(
			f"chmod 770 /var/lib/mysql/{self.database_name}"
		)
		if not success:
			self.reload()
			self.status = "Failure"
			self.save(ignore_permissions=True)
			return
		agent = Agent(self.database_server, "Database Server")
		job = agent.physical_backup_database(site, self)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)

	def run_ansible_command_in_database_server(self, command: str) -> bool:
		virtual_machine_ip = frappe.db.get_value(
			"Virtual Machine",
			frappe.get_value("Database Server", self.database_server, "virtual_machine"),
			"public_ip_address",
		)
		result = AnsibleAdHoc(sources=f"{virtual_machine_ip},").run(command, self.name)[0]
		success = result.get("status") == "Success"
		if not success:
			pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
			frappe.log_error(
				"During physical backup creation, failed to execute command in database server",
				message=pretty_result,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
			comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
			self.add_comment(text=comment)
		return success

	def create_database_snapshot(self):
		if self.database_snapshot:
			# Snapshot already exists, So no need to create a new one
			return

		server = frappe.get_value("Site", self.site, "server")
		database_server = frappe.get_value("Server", server, "database_server")
		virtual_machine: VirtualMachine = frappe.get_doc(
			"Virtual Machine", frappe.get_value("Database Server", database_server, "virtual_machine")
		)

		cache_key = f"volume_active_snapshot:{self.database_server}"

		max_retries = 3
		while max_retries > 0:
			is_ongoing_snapshot = frappe.utils.cint(frappe.cache.get_value(cache_key, expires=True))
			if not is_ongoing_snapshot:
				break
			time.sleep(2)
			max_retries -= 1

		if frappe.cache.get_value(cache_key, expires=True):
			raise OngoingSnapshotError("Snapshot creation per volume rate exceeded")

		frappe.cache.set_value(
			cache_key,
			1,
			expires_in_sec=15,
		)

		virtual_machine.create_snapshots(exclude_boot_volume=True, physical_backup=True)
		if len(virtual_machine.flags.created_snapshots) == 0:
			frappe.throw("Failed to create a snapshot for the database server")
		frappe.db.set_value(
			"Site Backup", self.name, "database_snapshot", virtual_machine.flags.created_snapshots[0]
		)

	def autocorrect_bench_permissions(self):
		"""
		Run this whenever a Site Backup fails with the error
		"[Errno 13]: Permission denied".
		"""
		job = frappe.db.get_value("Agent Job", self.job, ["bench", "server", "output"], as_dict=True)
		import re

		play_exists = frappe.db.get_value(
			"Ansible Play",
			filters={
				"play": "Correct Bench Permissions",
				"status": ["in", ["Pending", "Running"]],
				"server": job.server,
				"variables": ["like", "f%{job.bench}%"],
			},
		)

		if job.output and not play_exists and re.search(r"\[Errno 13\] Permission denied", job.output):
			try:
				bench = frappe.get_doc("Bench", job.bench)
				bench.correct_bench_permissions()
				return True
			except Exception:
				frappe.log_error(
					"Failed to correct bench permissions.",
					reference_doctype=self.doctype,
					reference_name=self.name,
				)
				return False
		return False

	def fix_global_search_indexes(self):
		"""
		Run this whenever Backup Job fails because of broken global search indexes and regenerate them.
		"""
		job = frappe.db.get_value("Agent Job", self.job, ["bench", "server", "output"], as_dict=True)

		if job.output and "Couldn't execute 'show create table `__global_search`'" in job.output:
			try:
				agent = Agent(self.server)
				agent.create_agent_job("Fix global search", "fix_global_search")
			except Exception:
				frappe.log_error(
					"Failed to fix global search indexes",
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

	@classmethod
	def offsite_backup_exists(cls, site: str, day: date) -> bool:
		return cls.backup_exists(site, day, {"offsite": True})

	@classmethod
	def backup_exists(cls, site: str, day: date, filters: dict):
		base_filters = {
			"creation": ("between", [day, day]),
			"site": site,
			"status": "Success",
		}
		return frappe.get_all("Site Backup", {**base_filters, **filters})

	@classmethod
	def file_backup_exists(cls, site: str, day: date) -> bool:
		return cls.backup_exists(site, day, {"with_files": True})


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site Backup")


class OngoingSnapshotError(Exception):
	"""Exception raised when other snapshot creation is ongoing"""

	pass


def track_offsite_backups(site: str, backup_data: dict, offsite_backup_data: dict) -> tuple:
	remote_files = {"database": None, "site_config": None, "public": None, "private": None}

	if offsite_backup_data:
		bucket = get_backup_bucket(frappe.db.get_value("Site", site, "cluster"))
		for type, backup in backup_data.items():
			file_name, file_size = backup["file"], backup["size"]
			file_path = offsite_backup_data.get(file_name)

			file_types = {
				"database": "application/x-gzip",
				"site_config": "application/json",
			}
			if file_path:
				remote_file = frappe.get_doc(
					{
						"doctype": "Remote File",
						"site": site,
						"file_name": file_name,
						"file_path": file_path,
						"file_size": file_size,
						"file_type": file_types.get(type, "application/x-tar"),
						"bucket": bucket,
					}
				)
				remote_file.save()
				add_tag("Offsite Backup", remote_file.doctype, remote_file.name)
				remote_files[type] = remote_file.name

	return (
		remote_files["database"],
		remote_files["site_config"],
		remote_files["public"],
		remote_files["private"],
	)


def process_backup_site_job_update(job):
	backups = frappe.get_all("Site Backup", fields=["name", "status"], filters={"job": job.name}, limit=1)
	if not backups:
		return
	backup = backups[0]
	if job.status != backup.status:
		status = job.status
		if job.status == "Delivery Failure":
			status = "Failure"

		if job.status == "Success":
			if frappe.get_value("Site Backup", backup.name, "physical"):
				doc: SiteBackup = frappe.get_doc("Site Backup", backup.name)
				doc.files_availability = "Available"
				doc.status = "Success"
				doc.save()
			else:
				frappe.db.set_value("Site Backup", backup.name, "status", status)
				job_data = json.loads(job.data)
				backup_data, offsite_backup_data = job_data["backups"], job_data["offsite"]
				(
					remote_database,
					remote_config_file,
					remote_public,
					remote_private,
				) = track_offsite_backups(job.site, backup_data, offsite_backup_data)

				site_backup_dict = {
					"files_availability": "Available",
					"database_size": backup_data["database"]["size"],
					"database_url": backup_data["database"]["url"],
					"database_file": backup_data["database"]["file"],
					"remote_database_file": remote_database,
				}

				if "site_config" in backup_data:
					site_backup_dict.update(
						{
							"config_file_size": backup_data["site_config"]["size"],
							"config_file_url": backup_data["site_config"]["url"],
							"config_file": backup_data["site_config"]["file"],
							"remote_config_file": remote_config_file,
						}
					)

				if "private" in backup_data and "public" in backup_data:
					site_backup_dict.update(
						{
							"private_size": backup_data["private"]["size"],
							"private_url": backup_data["private"]["url"],
							"private_file": backup_data["private"]["file"],
							"remote_public_file": remote_public,
							"public_size": backup_data["public"]["size"],
							"public_url": backup_data["public"]["url"],
							"public_file": backup_data["public"]["file"],
							"remote_private_file": remote_private,
						}
					)

				frappe.db.set_value("Site Backup", backup.name, site_backup_dict)
		else:
			site_backup: SiteBackup = frappe.get_doc("Site Backup", backup.name)
			site_backup.status = status
			site_backup.save()


def get_backup_bucket(cluster, region=False):
	bucket_for_cluster = frappe.get_all("Backup Bucket", {"cluster": cluster}, ["name", "region"], limit=1)
	default_bucket = frappe.db.get_single_value("Press Settings", "aws_s3_bucket")

	if region:
		return bucket_for_cluster[0] if bucket_for_cluster else default_bucket
	return bucket_for_cluster[0]["name"] if bucket_for_cluster else default_bucket


def process_deactivate_site_job_update(job: AgentJob):
	if job.reference_doctype != "Site Backup":
		return

	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return

	status = {
		"Success": "Success",
		"Failure": "Failure",
		"Delivery Failure": "Failure",
	}[job.status]

	if frappe.get_value("Site Backup", job.reference_name, "status") == status:
		return

	backup: SiteBackup = frappe.get_doc("Site Backup", job.reference_name)
	if status == "Failure":
		backup.status = "Failure"
		backup.save()
	elif status == "Success":
		backup.start_backup()


def on_doctype_update():
	frappe.db.add_index("Site Backup", ["files_availability", "job"])


def _create_site_backup_from_agent_job(job: "AgentJob"):
	"""
	Create Site Backup and Remote File records from archive site or uninstall app agent job's response.
	"""
	try:
		from press.press.doctype.site_backup.site_backup import track_offsite_backups

		if (job.job_type not in ["Archive Site", "Uninstall App from Site"]) or not job.data:
			return
		if not _check_backup_steps_status(job.name):
			return

		job_data = json.loads(job.data)
		backup_data = job_data.get("backups")
		offsite_backup_data = job_data.get("offsite", {})

		if not backup_data or not offsite_backup_data:
			return

		(
			remote_database,
			remote_config_file,
			remote_public,
			remote_private,
		) = track_offsite_backups(job.site, backup_data, offsite_backup_data)

		site_server = frappe.db.get_value("Site", job.site, "server")
		site_backup = frappe.get_doc(
			{
				"doctype": "Site Backup",
				"site": job.site,
				"server": site_server,
				"status": "Success",
				"with_files": True,
				"offsite": True,
				"job": job.name,
				"files_availability": "Available",
				"database_size": backup_data["database"]["size"],
				"database_url": backup_data["database"]["url"],
				"database_file": backup_data["database"]["file"],
				"remote_database_file": remote_database,
			}
		)

		if "site_config" in backup_data:
			site_backup.config_file_size = backup_data["site_config"]["size"]
			site_backup.config_file_url = backup_data["site_config"]["url"]
			site_backup.config_file = backup_data["site_config"]["file"]
			site_backup.remote_config_file = remote_config_file

		if "private" in backup_data and "public" in backup_data:
			site_backup.private_size = backup_data["private"]["size"]
			site_backup.private_url = backup_data["private"]["url"]
			site_backup.private_file = backup_data["private"]["file"]
			site_backup.remote_private_file = remote_private

			site_backup.public_size = backup_data["public"]["size"]
			site_backup.public_url = backup_data["public"]["url"]
			site_backup.public_file = backup_data["public"]["file"]
			site_backup.remote_public_file = remote_public

		site_backup.flags.skip_backup_after_insert = True
		site_backup.insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(
			f"Failed to create Site Backup record from {job.job_type} agent job: {e!s}",
			reference_doctype="Agent Job",
			reference_name=job.name,
		)


def _check_backup_steps_status(agent_job: str) -> bool:
	"""
	Check if Backup Site and Upload Site Backup to S3 steps both succeeded.
	"""
	try:
		steps = frappe.get_all(
			"Agent Job Step",
			filters={
				"agent_job": agent_job,
				"step_name": ("in", ["Backup Site", "Upload Site Backup to S3"]),
				"status": "Success",
			},
		)
		return len(steps) == 2
	except Exception:
		return False

