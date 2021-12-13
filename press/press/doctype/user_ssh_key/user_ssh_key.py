# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
import base64
import hashlib
from frappe import safe_decode
from frappe.model.document import Document


class UserSSHKey(Document):
	def validate(self):
		self.generate_ssh_fingerprint()

	def generate_ssh_fingerprint(self):
		ssh_key_b64 = base64.b64decode(self.ssh_public_key.strip().split()[1])
		sha256_sum = hashlib.sha256()
		sha256_sum.update(ssh_key_b64)
		self.ssh_fingerprint = safe_decode(base64.b64encode(sha256_sum.digest()))
