# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


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
		else:
			self.generate_certificate_signing_request()
			self.sign_certificate_signing_request()
			self.generate_chain_certificate()
		self.extract_certificate_details()

	def setup_directory(self):
		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)
		os.mkdir(self.directory)

		os.mkdir(self.new_certificates_directory)
		Path(self.database_file).touch()
		with open(self.serial_file, "w") as f:
			f.write(f"{secrets.randbits(16*8):0{32}x}\n")

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

	def generate_certificate_signing_request(self):
		self.run(
			f"openssl req -new -config {self.openssl_config_file} -key"
			f" {self.private_key_file} -out {self.certificate_signing_request_file}"
		)
		os.chmod(self.certificate_signing_request_file, 444)

	def sign_certificate_signing_request(self):
		parent = frappe.get_doc(self.doctype, self.parent_authority)
		self.run(
			f"openssl ca -batch -notext -days {self.validity_days} -config"
			f" {parent.openssl_config_file} -extensions v3_intermediate_ca -in"
			f" {self.certificate_signing_request_file} -out {self.certificate_file}"
		)
		os.chmod(self.certificate_file, 444)

	def generate_chain_certificate(self):
		parent = frappe.get_doc(self.doctype, self.parent_authority)
		with open(self.certificate_file) as f:
			certificate = f.read()
		with open(parent.certificate_file) as f:
			certificate += f.read()
		with open(self.certificate_chain_file, "w") as f:
			f.write(certificate)
		os.chmod(self.certificate_chain_file, 444)

	def extract_certificate_details(self):
		with open(self.certificate_file) as f:
			certificate = f.read()

		x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
		self.decoded_certificate = OpenSSL.crypto.dump_certificate(
			OpenSSL.crypto.FILETYPE_TEXT, x509
		).decode()

		self.issued_on = datetime.strptime(x509.get_notBefore().decode(), "%Y%m%d%H%M%SZ")
		self.expires_on = datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")

	def on_trash(self):
		if os.path.exists(self.directory):
			shutil.rmtree(self.directory)
		children = frappe.get_all(self.doctype, {"parent_authority": self.name})
		for child in children:
			frappe.delete_doc(self.doctype, child.name)

	@property
	def certificate_chain_file(self):
		return os.path.join(self.directory, "chain.pem")

	@property
	def certificate_file(self):
		return os.path.join(self.directory, "cert.pem")

	@property
	def certificate_signing_request_file(self):
		return os.path.join(self.directory, "csr.pem")

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
		return os.path.join(self.directory, "key.pem")

	@property
	def serial_file(self):
		return os.path.join(self.directory, "serial")
