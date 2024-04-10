# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import shlex
import subprocess
import frappe
import base64
import struct
from frappe.model.document import Document


class SSHKeyValueError(ValueError):
	pass


class SSHFingerprintError(ValueError):
	pass


class UserSSHKey(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_default: DF.Check
		ssh_fingerprint: DF.Data | None
		ssh_public_key: DF.Code
		user: DF.Link
	# end: auto-generated types

	dashboard_fields = ["ssh_fingerprint", "is_default", "user"]
	dashboard_actions = ["delete"]

	valid_key_types = [
		"ssh-rsa",
		"ssh-ed25519",
		"ecdsa-sha2-nistp256",
		"ecdsa-sha2-nistp384",
		"ecdsa-sha2-nistp521",
		"sk-ecdsa-sha2-nistp256@openssh.com",
		"sk-ssh-ed25519@openssh.com",
	]

	def check_embedded_key_type(self, key_type: str, key_bytes: bytes):
		type_len = struct.unpack(">I", key_bytes[:4])[0]  # >I is big endian unsigned int
		offset = 4 + type_len
		embedded_type = key_bytes[4:offset]
		if embedded_type.decode("utf-8") != key_type:
			raise SSHKeyValueError(f"Key type {key_type} does not match key")

	def validate(self):
		msg = "You must supply a key in OpenSSH public key format. Please try copy/pasting the key using one of the commands in documentation."
		try:
			key_type, key, *comment = self.ssh_public_key.strip().split()
			if key_type not in self.valid_key_types:
				raise SSHKeyValueError(
					f"Key type has to be one of {', '.join(self.valid_key_types)}"
				)
			key_bytes = base64.b64decode(key)
			self.check_embedded_key_type(key_type, key_bytes)
			self.generate_ssh_fingerprint(key_bytes)
		except SSHKeyValueError as e:
			frappe.throw(
				f"{str(e)}\n{msg}",
			)
		except Exception:
			frappe.throw(msg)

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

	def generate_ssh_fingerprint(self, key_bytes: bytes):
		try:
			return (
				subprocess.check_output(
					shlex.split("ssh-keygen -lf -"), stderr=subprocess.STDOUT, input=key_bytes
				)
				.decode()
				.split()[1]
			)
		except subprocess.CalledProcessError as e:
			raise SSHKeyValueError(f"Error generating fingerprint: {e.output.decode()}")
