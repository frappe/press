# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import hmac
import hashlib
import json
from frappe.model.document import Document


class GitHubWebhookLog(Document):
	def validate(self):
		secret = frappe.db.get_single_value("Press Settings", "github_webhook_secret")
		digest = hmac.HMAC(secret.encode(), self.payload.encode(), hashlib.sha1)
		if not hmac.compare_digest(digest.hexdigest(), self.signature):
			frappe.throw("Invalid Signature")
		payload = json.loads(self.payload)
		self.payload = json.dumps(payload, indent=4, sort_keys=True)
