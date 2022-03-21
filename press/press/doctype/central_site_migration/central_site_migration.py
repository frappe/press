# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.telegram_utils import Telegram
from press.runner import Ansible
from press.utils import log_error

central_username = "central@frappecloud.com"
central_user_password = "wbFzfU62DALuQPZ"


def get_ongoing_migration(site: str, scheduled=False):
	ongoing_statuses = ["Pending", "Running"]
	if scheduled:
		ongoing_statuses.append("Scheduled")
	return frappe.db.exists(
		"Central Site Migration", {"site": site, "status": ("in", ongoing_statuses)}
	)


class CentralSiteMigration(Document):
	def before_insert(self):
		if get_ongoing_migration(self.site, scheduled=True):
			frappe.throw("Ongoing/Scheduled Site Migration for that site exists.")

	@frappe.whitelist()
	def start(self):
		self.status = "Pending"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_start", queue="long")

	def _start(self):
		try:
			ansible = Ansible(
				user="frappe",
				port=2332,
				playbook="central-site-migration.yml",
				server=frappe.get_doc("Central Server", self.server),
				variables={
					"bench": self.bench,
					"site": self.site,
					"version": self.version,
					"username": central_username,
					"password": central_user_password,
				},
			)
			self.reload()
			self.play = ansible.play
			self.status = "Running"
			self.save()
			frappe.db.commit()
			play = ansible.run()
			if play.status == "Success":
				self.status = "Success"
			else:
				self.fail()
		except Exception:
			self.fail()
			log_error("Central Site Migration Exception", migration=self.as_dict())
		self.save()

	def fail(self):
		self.status = "Failure"
		domain = frappe.get_value("Press Settings", "Press Settings", "domain")
		message = f"""
Migration for *{self.site}* failed.
Now look what you did!

[Central Site Migration]({domain}{self.get_url()})
"""
		chat_id = (
			frappe.db.get_value("Press Settings", "Press Settings", "telegram_alert_chat_id"),
		)
		telegram = Telegram(chat_id)
		telegram.send(message)


def start_one_migration():
	frappe.get_last_doc(
		"Central Site Migration",
		{"status": "Scheduled", "scheduled_time": ("is", "not set")},
		order_by="creation asc",
	).start()
