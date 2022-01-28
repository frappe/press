# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import base64
import binascii
import hashlib
import os
import re
import shlex
import subprocess

from frappe.model.document import Document


class SSHCertificate(Document):
	def validate(self):
		self.validate_public_key()

	def validate_public_key(self):
		try:
			ssh_key_b64 = base64.b64decode(self.ssh_public_key.strip().split()[1])
			sha256_sum = hashlib.sha256()
			sha256_sum.update(ssh_key_b64)
			self.ssh_fingerprint = base64.b64encode(sha256_sum.digest()).decode()
			self.key_type = self.ssh_public_key.strip().split()[0].split("-")[1]
		except binascii.Error:
			frappe.throw("Attached text is a not valid public key")

		self.key_type = self.ssh_public_key.strip().split()[0].split("-")[1]
		if not self.key_type:
			frappe.throw("Could not guess the key type. Please check your public key.")
