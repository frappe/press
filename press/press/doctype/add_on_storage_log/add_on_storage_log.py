# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import BaseServer


class AddOnStorageLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		adding_storage: DF.Float
		available_disk_space: DF.Float
		current_disk_usage: DF.Float
		database_server: DF.Link | None
		extend_ec2_play: DF.Link | None
		is_auto_triggered: DF.Check
		is_warning: DF.Check
		mountpoint: DF.Data | None
		notification_sent: DF.Check
		server: DF.Link | None
	# end: auto-generated types

	def send_notification(self):
		"""Send add on storage notification / warning"""
		server: BaseServer = frappe.get_cached_doc(
			"Server" if self.server else "Database Server", self.server or self.database_server
		)
		notify_email = frappe.get_value("Team", server.team, "notify_email")

		frappe.sendmail(
			recipients=notify_email,
			subject=f"Important: Server {server.name} storage space at 90%",
			template="enabled_auto_disk_expansion" if not self.is_warning else "disabled_auto_disk_expansion",
			args={
				"server": server.name,
				"current_disk_usage": f"{self.current_disk_usage} GiB",
				"available_disk_space": f"{self.available_disk_space} GiB",
				"increase_by": f"{self.adding_storage} GiB",
				"used_storage_percentage": "90%",
			},
		)

		self.notification_sent = True
		self.save()


def insert_addon_storage_log(
	adding_storage: float,
	available_disk_space: float,
	current_disk_usage: float,
	mountpoint: str,
	is_auto_triggered: bool,
	is_warning: bool,
	database_server: str | None = None,
	server: str | None = None,
) -> AddOnStorageLog | None:
	doctype = "Server" if server else "Database Server"
	name = server or database_server
	server: BaseServer = frappe.get_cached_doc(doctype, name)

	if (
		(server.provider not in ("AWS EC2", "OCI"))
		or (server.provider == "AWS EC2" and server.time_to_wait_before_updating_volume)
	) and not is_warning:
		# This won't trigger ec2 play in this case.
		# We might not need skip_if_exists at all also don't skip if is_warning
		return None

	add_on_storage_log: AddOnStorageLog = frappe.get_doc(
		{
			"doctype": "Add On Storage Log",
			"adding_storage": adding_storage,
			"available_disk_space": available_disk_space,
			"current_disk_usage": current_disk_usage,
			"mountpoint": mountpoint,
			"notification_sent": is_warning,  # If is warning we send the notification immediately,
			"is_auto_triggered": is_auto_triggered,
			"is_warning": is_warning,
			"server": server,
			"database_server": database_server,
		}
	)
	add_on_storage_log.insert(ignore_permissions=True)

	# In cases of warnings send emails immediately
	if add_on_storage_log.is_warning:
		add_on_storage_log.send_notification()

	return add_on_storage_log


def send_disk_extention_notification():
	logs = frappe.get_all(
		"Add On Storage Log",
		{
			"notification_sent": 0,
			"creation": ("between", [frappe.utils.add_to_date(days=-1), frappe.utils.now()]),
			"mountpoint": ("!=", "/"),
		},
		pluck="name",
		limit=100,
	)

	for log in logs:
		add_on_storage_log: AddOnStorageLog = frappe.get_doc("Add On Storage Log", log)
		if (
			add_on_storage_log.extend_ec2_play
			and frappe.get_value("Ansible Play", add_on_storage_log.extend_ec2_play, "status") == "Success"
		):
			# Only send notification if extend ec2 play has run successfully
			add_on_storage_log.send_notification()
