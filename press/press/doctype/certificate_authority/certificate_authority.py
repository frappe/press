# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os
import secrets
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import OpenSSL

import frappe
from frappe.model.document import Document
from press.utils import developer_mode_only


class CertificateAuthority(Document):
	def onload(self):
		developer_mode_only()

	def validate(self):
		developer_mode_only()
		self.setup_directory()
		self.generate_private_key()
		if self.is_root_ca:
			self.generate_root_certificate()
		self.extract_certificate_details()

	def setup_directory(self):
		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)
		os.mkdir(self.directory)

		os.mkdir(self.new_certificates_directory)
		Path(self.database_file).touch()
		with open(self.serial_file, "w") as f:
			f.write(f"{secrets.randbits(16*8):x}")

		template = "root.conf" if self.is_root_ca else "intermediate.conf"
		template = f"press/press/doctype/certificate_authority/{template}"
		with open(self.openssl_config_file, "w") as f:
			openssl_config = frappe.render_template(template, {"doc": self}, is_path=True)
			f.write(openssl_config)

	def run(self, command):
		return subprocess.check_output(shlex.split(command)).decode()

	def generate_private_key(self):
		self.run(f"openssl genrsa -out {self.private_key_file} {self.rsa_key_size}")
		os.chmod(self.private_key_file, 400)

	def generate_root_certificate(self):
		self.run(
			f"openssl req -new -x509 -days {self.validity_days} -config"
			f" {self.openssl_config_file} -key {self.private_key_file} -out"
			f" {self.certificate_file}"
		)
		os.chmod(self.certificate_file, 444)

	def extract_certificate_details(self):
		with open(self.certificate_file) as f:
			certificate = f.read()

		x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
		self.decoded_certificate = OpenSSL.crypto.dump_certificate(
			OpenSSL.crypto.FILETYPE_TEXT, x509
		).decode()

		self.issued_on = datetime.strptime(x509.get_notBefore().decode(), "%Y%m%d%H%M%SZ")
		self.expires_on = datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")

	@property
	def certificate_chain_file(self):
		return os.path.join(self.directory, "ca.chain.pem")

	@property
	def certificate_file(self):
		return os.path.join(self.directory, "ca.cert.pem")

	@property
	def certificate_signing_request_file(self):
		return os.path.join(self.directory, "ca.csr.pem")

	@property
	def database_file(self):
		return os.path.join(self.directory, "index.txt")

	@property
	def new_certificates_directory(self):
		return os.path.join(self.directory, "newcerts")

	@property
	def openssl_config_file(self):
		return os.path.join(self.directory, "openssl.conf")

	@property
	def private_key_file(self):
		return os.path.join(self.directory, "ca.key.pem")

	@property
	def serial_file(self):
		return os.path.join(self.directory, "serial")

