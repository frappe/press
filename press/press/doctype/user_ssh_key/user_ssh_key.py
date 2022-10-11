# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import base64
import hashlib
from frappe import safe_decode
from frappe.model.document import Document


class UserSSHKey(Document):
	def validate(self):
		self.generate_ssh_fingerprint()

	def after_insert(self):
		if self.is_default:
			self.make_other_keys_non_default()

	def on_update(self):
		if self.has_value_changed("is_default") and self.is_default:
			self.make_other_keys_non_default()

	def make_other_keys_non_default(self):
		frappe.db.set_value(
			"User SSH Key",
			{"user": self.user, "is_default": True, "name": ("!=", self.name)},
			"is_default",
			False,
		)

	def generate_ssh_fingerprint(self):
		try:
			ssh_key_b64 = base64.b64decode(self.ssh_public_key.strip().split()[1])
			sha256_sum = hashlib.sha256()
			sha256_sum.update(ssh_key_b64)
			self.ssh_fingerprint = safe_decode(base64.b64encode(sha256_sum.digest()))
		except Exception:
			frappe.throw("Key is invalid. You must supply a key in OpenSSH public key format")
