# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime
import os
import subprocess
import OpenSSL
from frappe.utils.password import get_decrypted_password
from frappe.model.document import Document
from press.utils import log_error


class TLSCertificate(Document):
	def autoname(self):
		if self.wildcard:
			self.name = f"*.{self.domain}"
		else:
			self.name = self.domain

	def after_insert(self):
		self.obtain_certificate()

	def obtain_certificate(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_obtain_certificate", enqueue_after_commit=True
		)

	def _obtain_certificate(self):
		try:
			settings = frappe.get_doc("Press Settings", "Press Settings")
			if self.wildcard:
				self._obtain_wildcard_certificate(settings)
			else:
				self._obtain_default_certificate(settings)
			self._extract_certificate_details(settings)
			self.status = "Active"
		except Exception:
			self.status = "Failure"
			log_error("TLS Certificate Exception", certificate=self.name)
		self.save()
		self.trigger_site_domain_callback()

	def trigger_site_domain_callback(self):
		domain = frappe.db.get_value("Site Domain", {"tls_certificate": self.name}, "name")
		if domain:
			frappe.get_doc("Site Domain", domain).process_tls_certificate_update()

	def _obtain_wildcard_certificate(self, settings):
		environment = os.environ
		environment.update(
			{
				"AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
				"AWS_SECRET_ACCESS_KEY": get_decrypted_password(
					"Press Settings", "Press Settings", "aws_secret_access_key"
				),
			}
		)
		command = self._certbot_command(settings)
		subprocess.check_output(command.split(), env=environment)

	def _obtain_default_certificate(self, settings):
		command = self._certbot_command(settings)
		subprocess.check_output(command.split())

	def _certbot_command(self, settings):
		certbot_directory = settings.certbot_directory
		if self.wildcard:
			plugin = "--dns-route53"
		else:
			plugin = f"--webroot --webroot-path {settings.webroot_directory}"

		staging = ""  # "--staging " if frappe.conf.developer_mode else ""

		command = (
			f"certbot certonly --quiet {plugin} {staging}--logs-dir"
			f" {certbot_directory}/logs --work-dir {certbot_directory} --config-dir"
			f" {certbot_directory} --agree-tos --eff-email --email"
			f" {settings.eff_registration_email} --must-staple --staple-ocsp"
			f" --rsa-key-size {self.rsa_key_size} --cert-name {self.name} --domains"
			f" {self.name}"
		)

		return command

	def _extract_certificate_details(self, settings):
		with open(f"{settings.certbot_directory}/live/{self.name}/fullchain.pem", "r") as f:
			self.fullchain = f.read()
		with open(f"{settings.certbot_directory}/live/{self.name}/chain.pem", "r") as f:
			self.chain = f.read()
		with open(f"{settings.certbot_directory}/live/{self.name}/privkey.pem", "r") as f:
			self.privkey = f.read()

		x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.fullchain)
		self.decoded_certificate = OpenSSL.crypto.dump_certificate(
			OpenSSL.crypto.FILETYPE_TEXT, x509
		).decode()
		self.expiry = datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")
