# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import base64
import binascii
import hashlib
import os
import re
import shlex
import subprocess
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.ssh_certificate_authority.ssh_certificate_authority import (
		SSHCertificateAuthority,
	)


class SSHCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		certificate_details: DF.Code | None
		certificate_type: DF.Literal["User", "Host"]
		group: DF.Link | None
		key_type: DF.Data | None
		serial_number: DF.Int
		ssh_certificate: DF.Code | None
		ssh_certificate_authority: DF.Link | None
		ssh_certificate_authority_public_key: DF.Code | None
		ssh_fingerprint: DF.Data | None
		ssh_public_key: DF.Code
		user: DF.Link | None
		user_ssh_key: DF.Link | None
		valid_until: DF.Datetime | None
		validity: DF.Literal["1h", "3h", "6h", "30d"]
	# end: auto-generated types

	def validate(self):
		self.validate_public_key()
		self.validate_existing_certificates()
		self.validate_validity()
		self.validate_certificate_authority()

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

	def validate_validity(self):
		if self.certificate_type == "User" and self.validity not in ("1h", "3h", "6h"):
			frappe.throw("User certificates can only be valid for a short duration")

	def validate_certificate_authority(self):
		if not self.ssh_certificate_authority:
			self.ssh_certificate_authority = frappe.db.get_single_value(
				"Press Settings", "ssh_certificate_authority"
			)
		if not self.ssh_certificate_authority:
			frappe.throw(
				"SSH Certificate Authority is required to generate SSH certificates",
				frappe.ValidationError,
			)

	def validate_existing_certificates(self):
		if frappe.get_all(
			"SSH Certificate",
			{
				"user_ssh_key": self.user_ssh_key,
				"valid_until": [">", frappe.utils.now()],
				"group": self.group,
			},
		):
			frappe.throw("A valid certificate already exists.")

	def create_public_key_file(self):
		with open(self.public_key_file, "w") as file:
			file.write(self.ssh_public_key)

	def after_insert(self):
		self.serial_number = self.name[5:]
		self.create_public_key_file()
		self.generate_certificate()
		self.extract_certificate_details()
		frappe.local.role_permissions = {}
		self.save()

	def generate_certificate(self):
		ca: "SSHCertificateAuthority" = frappe.get_doc(
			"SSH Certificate Authority", self.ssh_certificate_authority
		)
		ca.sign(
			self.user,
			[self.group],
			f"+{self.validity}",
			self.public_key_file,
			self.serial_number,
		)
		self.read_certificate()

	def run(self, command):
		try:
			return subprocess.check_output(
				shlex.split(command), stderr=subprocess.STDOUT
			).decode()
		except subprocess.CalledProcessError as e:
			log_error("Command failed", output={e.output.decode()}, doc=self)
			raise

	def extract_certificate_details(self):
		self.certificate_details = self.run(f"ssh-keygen -Lf {self.certificate_file}")
		regex = re.compile("Valid:.*\n")
		self.valid_until = regex.findall(self.certificate_details)[0].strip().split()[-1]

	def read_certificate(self):
		with open(self.certificate_file) as file:
			self.ssh_certificate = file.read()

	@property
	def public_key_file(self):
		return os.path.join("/tmp", f"id_{self.key_type}-{self.serial_number}.pub")

	@property
	def certificate_file(self):
		return os.path.join("/tmp", f"id_{self.key_type}-{self.serial_number}-cert.pub")
