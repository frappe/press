# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.runner import Ansible
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.server.server import Server


class SecurityUpdateCheck(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		play: DF.Link | None
		server: DF.DynamicLink
		server_type: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def after_insert(self):
		self.start()

	@frappe.whitelist()
	def start(self):
		self.status = "Pending"
		self.save()
		frappe.db.commit()
		frappe.enqueue_doc(self.doctype, self.name, "_start", queue="short")

	def _start(self):
		try:
			server: Server = frappe.get_doc(self.server_type, self.server)
			ansible = Ansible(
				playbook="security_update.yml",
				server=server,
				user=server.ssh_user or "root",
				port=server.ssh_port or 22,
				variables={"validate_pending_security_updates": True},
			)
			self.reload()
			self.play = ansible.play
			self.status = "Running"
			self.save()
			frappe.db.commit()
			play = ansible.run()
			if play.status == "Success":
				self.succeed()
			else:
				self.fail()
		except Exception:
			log_error("Security Update Check Exception", scan=self.as_dict())
			self.fail()
		self.save()

	def succeed(self):
		self.status = "Success"

	def fail(self):
		self.status = "Failure"
		domain = frappe.get_value("Press Settings", "Press Settings", "domain")
		message = f"""
Security Update Check for *{self.server}* failed.

[Security Update Check]({domain}{self.get_url()})
"""
		TelegramMessage.enqueue(message=message)
