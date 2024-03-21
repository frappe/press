# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.telegram_utils import Telegram


class AuditLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		audit_type: DF.Literal[
			"Bench Field Check",
			"Backup Record Check",
			"Offsite Backup Check",
			"Restore Offsite Backup of Site",
			"App Server Replica Dirs Check",
			"Unbilled Subscription Check",
			"Billing Audit",
			"Partner Billing Audit",
		]
		log: DF.Code | None
		status: DF.Literal["Success", "Failure"]
		telegram_group: DF.Link | None
		telegram_group_topic: DF.Data | None
	# end: auto-generated types

	def after_insert(self):
		if self.status == "Failure":
			self.notify()

	def notify(self):
		domain = frappe.get_value("Press Settings", "Press Settings", "domain")
		message = f"""
			*FAILED AUDIT*
			[{self.audit_type}]({domain}{self.get_url()})
			```
			{self.log[:3000]}
			```
		"""

		topic = self.telegram_topic or "Errors"
		group = self.telegram_group
		telegram = Telegram(topic=topic, group=group)
		telegram.send(message)
