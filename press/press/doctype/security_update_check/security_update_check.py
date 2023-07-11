# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.telegram_utils import Telegram
from press.runner import Ansible
from press.utils import log_error


class SecurityUpdateCheck(Document):
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
			_server = frappe.get_doc(self.server_type, self.server)
			ansible = Ansible(
				playbook="security_update_check.yml",
				server=_server,
				user =_server.ssh_user or "root",
				port=_server.ssh_port or 22,
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
		telegram = Telegram()
		telegram.send(message)
