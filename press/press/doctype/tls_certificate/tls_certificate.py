# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import os
import shlex
import subprocess
from datetime import datetime

import frappe
import OpenSSL
from frappe.model.document import Document

from press.api.site import check_dns_cname_a
from press.overrides import get_permission_query_conditions_for_doctype
from press.runner import Ansible
from press.utils import get_current_team, log_error


class TLSCertificate(Document):
	def autoname(self):
		if self.wildcard:
			self.name = f"*.{self.domain}"
		else:
			self.name = self.domain

	def after_insert(self):
		self.obtain_certificate()

	@frappe.whitelist()
	def obtain_certificate(self):
		user, session_data, team, = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(),
		)
		frappe.set_user(team)
		frappe.enqueue_doc(
			self.doctype, self.name, "_obtain_certificate", enqueue_after_commit=True
		)
		frappe.set_user(user)
		frappe.session.data = session_data

	@frappe.whitelist()
	def _obtain_certificate(self):
		try:
			settings = frappe.get_doc("Press Settings", "Press Settings")
			ca = LetsEncrypt(settings)
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
		if self.wildcard:
			self.trigger_server_tls_setup_callback()
			self._update_secondary_wildcard_domains()

	def _update_secondary_wildcard_domains(self):
		"""
		Install secondary wildcard domains on proxies.

		Skip install on servers using the same domain for it's own hostname.
		"""
		proxies_containing_domain = frappe.get_all(
			"Proxy Server Domain", {"domain": self.domain}, pluck="parent"
		)
		proxies_using_domain = frappe.get_all(
			"Proxy Server", {"domain": self.domain}, pluck="name"
		)
		proxies_containing_domain = set(proxies_containing_domain) - set(proxies_using_domain)
		for proxy_name in proxies_containing_domain:
			proxy = frappe.get_doc("Proxy Server", proxy_name)
			proxy.setup_wildcard_hosts()

	def trigger_server_tls_setup_callback(self):
		server_doctypes = [
			"Proxy Server",
			"Server",
			"Database Server",
			"Log Server",
			"Monitor Server",
			"Registry Server",
			"Analytics Server",
		]

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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"TLS Certificate"
)


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
			if frappe.conf.developer_mode:
				self._obtain_naked_with_dns()
			else:
				self._obtain_naked()

	def _obtain_wildcard(self):
		domain = frappe.get_doc("Root Domain", self.domain[2:])
		environment = os.environ
		environment.update(
			{
				"AWS_ACCESS_KEY_ID": domain.aws_access_key_id,
				"AWS_SECRET_ACCESS_KEY": domain.get_password("aws_secret_access_key"),
			}
		)
		self.run(self._certbot_command(), environment=environment)

	def _obtain_naked_with_dns(self):
		domain = frappe.get_all("Root Domain", pluck="name", limit=1)[0]
		domain = frappe.get_doc("Root Domain", domain)
		environment = os.environ
		environment.update(
			{
				"AWS_ACCESS_KEY_ID": domain.aws_access_key_id,
				"AWS_SECRET_ACCESS_KEY": domain.get_password("aws_secret_access_key"),
			}
		)
		self.run(self._certbot_command(), environment=environment)

	def _obtain_naked(self):
		if not os.path.exists(self.webroot_directory):
			os.mkdir(self.webroot_directory)
		self.run(self._certbot_command())

	def _certbot_command(self):
		if self.wildcard or frappe.conf.developer_mode:
			plugin = "--dns-route53"
		else:
			plugin = f"--webroot --webroot-path {self.webroot_directory}"

		staging = "--staging" if self.staging else ""
		force_renewal = "--keep" if frappe.conf.developer_mode else "--force-renewal"

		command = (
			f"certbot certonly {plugin} {staging} --logs-dir"
			f" {self.directory}/logs --work-dir {self.directory} --config-dir"
			f" {self.directory} {force_renewal} --agree-tos --eff-email --email"
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
