# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os
import shlex
import subprocess
from datetime import datetime

import OpenSSL

import frappe
from frappe.model.document import Document
from press.api.site import check_dns_cname_a
from press.runner import Ansible
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
			if frappe.conf.developer_mode and settings.use_backbone_ca:
				ca_class = Backbone
			else:
				ca_class = LetsEncrypt
			ca = ca_class(settings)
			(
				self.certificate,
				self.full_chain,
				self.intermediate_chain,
				self.private_key,
			) = ca.obtain(
				domain=self.domain, rsa_key_size=self.rsa_key_size, wildcard=self.wildcard
			)
			self._extract_certificate_details()
			self.status = "Active"
		except Exception:
			self.status = "Failure"
			log_error("TLS Certificate Exception", certificate=self.name)
		self.save()
		self.trigger_site_domain_callback()
		self.trigger_server_tls_setup_callback()

	def trigger_server_tls_setup_callback(self):
		if not self.wildcard:
			return

		server_doctypes = ["Proxy Server", "Server", "Database Server"]
		for server_doctype in server_doctypes:
			servers = frappe.get_all(
				server_doctype, {"status": "Active", "name": ("like", f"%.{self.domain}")}
			)
			for server in servers:
				server_doc = frappe.get_doc(server_doctype, server)
				update_server_tls_certifcate(server_doc, self)

	def trigger_site_domain_callback(self):
		domain = frappe.db.get_value("Site Domain", {"tls_certificate": self.name}, "name")
		if domain:
			frappe.get_doc("Site Domain", domain).process_tls_certificate_update()

	def _extract_certificate_details(self):
		x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.certificate)
		self.decoded_certificate = OpenSSL.crypto.dump_certificate(
			OpenSSL.crypto.FILETYPE_TEXT, x509
		).decode()
		self.issued_on = datetime.strptime(x509.get_notBefore().decode(), "%Y%m%d%H%M%SZ")
		self.expires_on = datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")


def renew_tls_certificates():
	pending = frappe.get_all(
		"TLS Certificate",
		fields=["name", "domain", "wildcard"],
		filters={"status": "Active", "expires_on": ("<", frappe.utils.add_days(None, 25))},
	)
	for certificate in pending:
		site = frappe.db.get_value(
			"Site Domain", {"tls_certificate": certificate.name, "status": "Active"}, "site"
		)
		if site:
			site_status = frappe.db.get_value("Site", site, "status")
			if site_status == "Active" and check_dns_cname_a(site, certificate.domain):
				certificate_doc = frappe.get_doc("TLS Certificate", certificate.name)
				certificate_doc._obtain_certificate()
				frappe.db.commit()
		if certificate.wildcard:
			certificate_doc = frappe.get_doc("TLS Certificate", certificate.name)
			certificate_doc._obtain_certificate()


def update_server_tls_certifcate(server, certificate):
	try:
		ansible = Ansible(
			playbook="tls.yml",
			server=server,
			variables={
				"certificate_private_key": certificate.private_key,
				"certificate_full_chain": certificate.full_chain,
				"certificate_intermediate_chain": certificate.intermediate_chain,
			},
		)
		ansible.run()
	except Exception:
		log_error("TLS Setup Exception", server=server.as_dict())


class BaseCA:
	def __init__(self, settings):
		self.settings = settings

	def obtain(self, domain, rsa_key_size=2048, wildcard=False):
		self.domain = f"*.{domain}" if wildcard else domain
		self.rsa_key_size = rsa_key_size
		self.wildcard = wildcard
		self._obtain()
		return self._extract()

	def _extract(self):
		with open(self.certificate_file) as f:
			certificate = f.read()
		with open(self.full_chain_file) as f:
			full_chain = f.read()
		with open(self.intermediate_chain_file) as f:
			intermediate_chain = f.read()
		with open(self.private_key_file) as f:
			private_key = f.read()

		return certificate, full_chain, intermediate_chain, private_key


class LetsEncrypt(BaseCA):
	def __init__(self, settings):
		super().__init__(settings)
		self.directory = settings.certbot_directory
		self.webroot_directory = settings.webroot_directory
		self.eff_registration_email = settings.eff_registration_email

		self.aws_access_key_id = settings.aws_access_key_id
		self.aws_secret_access_key = settings.get_password("aws_secret_access_key")

		# Staging CA provides certificates that are signed by an untrusted root CA
		# Only use to test certificate procurement/installation flows.
		# Reference: https://letsencrypt.org/docs/staging-environment/
		if frappe.conf.developer_mode and settings.use_staging_ca:
			self.staging = True
		else:
			self.staging = False

	def _obtain(self):
		if not os.path.exists(self.directory):
			os.mkdir(self.directory)
		if self.wildcard:
			self._obtain_wildcard()
		else:
			self._obtain_naked()

	def _obtain_wildcard(self):
		environment = os.environ
		environment.update(
			{
				"AWS_ACCESS_KEY_ID": self.aws_access_key_id,
				"AWS_SECRET_ACCESS_KEY": self.aws_secret_access_key,
			}
		)
		self.run(self._certbot_command(), environment=environment)

	def _obtain_naked(self):
		if not os.path.exists(self.webroot_directory):
			os.mkdir(self.webroot_directory)
		self.run(self._certbot_command())

	def _certbot_command(self):
		if self.wildcard:
			plugin = "--dns-route53"
		else:
			plugin = f"--webroot --webroot-path {self.webroot_directory}"

		staging = "--staging" if self.staging else ""

		command = (
			f"certbot certonly {plugin} {staging} --logs-dir"
			f" {self.directory}/logs --work-dir {self.directory} --config-dir"
			f" {self.directory} --force-renewal --agree-tos --eff-email --email"
			f" {self.eff_registration_email} --staple-ocsp"
			f" --rsa-key-size {self.rsa_key_size} --cert-name {self.domain} --domains"
			f" {self.domain}"
		)

		return command

	def run(self, command, environment=None):
		try:
			subprocess.check_output(
				shlex.split(command), stderr=subprocess.STDOUT, env=environment
			)
		except Exception as e:
			log_error("Certbot Exception", command=command, output=e.output.decode())
			raise e

	@property
	def certificate_file(self):
		return os.path.join(self.directory, "live", self.domain, "cert.pem")

	@property
	def full_chain_file(self):
		return os.path.join(self.directory, "live", self.domain, "fullchain.pem")

	@property
	def intermediate_chain_file(self):
		return os.path.join(self.directory, "live", self.domain, "chain.pem")

	@property
	def private_key_file(self):
		return os.path.join(self.directory, "live", self.domain, "privkey.pem")


class Backbone(BaseCA):
	def __init__(self, settings):
		super().__init__(settings)
		ca = settings.backbone_intermediate_ca
		self.ca = frappe.get_doc("Certificate Authority", ca)

	def run(self, command):
		try:
			subprocess.check_output(shlex.split(command), stderr=subprocess.STDOUT)
		except Exception as e:
			log_error("Backbone CA Exception", command=command, output=e.output.decode())
			raise e

	def _obtain(self):
		self.directory = os.path.join(self.ca.directory, "..", self.domain)
		if not os.path.exists(self.directory):
			os.mkdir(self.directory)

		template = "press/press/doctype/tls_certificate/server.conf"
		with open(self.openssl_config_file, "w") as f:
			openssl_config = frappe.render_template(template, {"doc": self}, is_path=True)
			f.write(openssl_config)

		self.generate_private_key()
		self.generate_certificate_signing_request()
		self.sign_certificate_signing_request()
		self.generate_intermediate_chain_certificate()
		self.generate_full_chain_certificate()

	def generate_private_key(self):
		self.run(f"openssl genrsa -out {self.private_key_file} {self.rsa_key_size}")
		os.chmod(self.private_key_file, 400)

	def generate_certificate_signing_request(self):
		self.run(
			f"openssl req -new -config {self.openssl_config_file} -key"
			f" {self.private_key_file} -out {self.certificate_signing_request_file}"
		)
		os.chmod(self.certificate_signing_request_file, 444)

	def sign_certificate_signing_request(self):
		self.run(
			"openssl ca -batch -notext -config"
			f" {self.ca.openssl_config_file} -extensions server_cert -in"
			f" {self.certificate_signing_request_file} -out {self.certificate_file}"
		)
		os.chmod(self.certificate_file, 444)

	def generate_intermediate_chain_certificate(self):
		with open(self.ca.certificate_file) as f:
			ca_certificate = f.read()
		with open(self.intermediate_chain_file, "w") as f:
			f.write(ca_certificate)
		os.chmod(self.intermediate_chain_file, 444)

	def generate_full_chain_certificate(self):
		with open(self.certificate_file) as f:
			fullchain = f.read()
		with open(self.intermediate_chain_file) as f:
			fullchain += f.read()
		with open(self.full_chain_file, "w") as f:
			f.write(fullchain)
		os.chmod(self.full_chain_file, 444)

	@property
	def openssl_config_file(self):
		return os.path.join(self.directory, "openssl.conf")

	@property
	def certificate_signing_request_file(self):
		return os.path.join(self.directory, "csr.pem")

	@property
	def certificate_file(self):
		return os.path.join(self.directory, "cert.pem")

	@property
	def full_chain_file(self):
		return os.path.join(self.directory, "fullchain.pem")

	@property
	def intermediate_chain_file(self):
		return os.path.join(self.directory, "chain.pem")

	@property
	def private_key_file(self):
		return os.path.join(self.directory, "key.pem")
