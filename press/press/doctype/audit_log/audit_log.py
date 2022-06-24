# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.telegram_utils import Telegram


class AuditLog(Document):
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
		telegram = Telegram()
		telegram.send(message)
