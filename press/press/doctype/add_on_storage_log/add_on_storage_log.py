# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server


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
		has_auto_increased: DF.Check
		mountpoint: DF.Data | None
		notification_sent: DF.Check
		reason: DF.SmallText | None
		server: DF.Link | None
	# end: auto-generated types

	def validate_existing_logs(self):
		logs_created_today = frappe.get_value(
			"Add On Storage",
			{
				"server": self.server,
				"database_server": self.database_server,
				"creation": (
					"between",
					[
						frappe.utils.add_to_date(days=-1),
						frappe.utils.now(),
					],
				),
			},
		)
		if logs_created_today:
			frappe.throw("A log for this machine already exists")

	def validate(self):
		self.validate_existing_logs()

	def send_notification(self):
		"""Send add on storage notification"""
		server: Server | DatabaseServer = frappe.get_cached_doc(
			"Server" if self.server else "Database Server", self.server or self.database_server
		)
		notify_email = frappe.get_value("Team", server.team, "notify_email")

		frappe.sendmail(
			recipients=notify_email,
			subject=f"Important: Server {server.name} storage space at 90%",
			template="enabled_auto_disk_expansion",
			args={
				"server": server.name,
				"current_disk_usage": f"{self.current_disk_usage} GiB",
				"available_disk_space": f"{self.available_disk_space} GiB",
				"increase_by": f"{self.adding_storage} GiB",
			},
		)


def get_teams_to_send_notifications_to():
	frappe.get_all("Add On Storage Log", {"notification_sent": 0}, pluck="name")
