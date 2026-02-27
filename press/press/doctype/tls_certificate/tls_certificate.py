# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING

import frappe
import OpenSSL
from frappe.model.document import Document
from frappe.query_builder.functions import Date

from press.exceptions import (
	DNSValidationError,
	TLSRetryLimitExceeded,
)
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.runner import Ansible
from press.utils import get_current_team, log_error
from press.utils.dns import check_dns_cname_a

if TYPE_CHECKING:
	from press.press.doctype.ansible_play.ansible_play import AnsiblePlay

AUTO_RETRY_LIMIT = 5
MANUAL_RETRY_LIMIT = 8


class TLSCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		certificate: DF.Code | None
		decoded_certificate: DF.Code | None
		domain: DF.Data
		error: DF.Code | None
		expires_on: DF.Datetime | None
		full_chain: DF.Code | None
		intermediate_chain: DF.Code | None
		issued_on: DF.Datetime | None
		private_key: DF.Code | None
		provider: DF.Literal["Let's Encrypt", "Other"]
		retry_count: DF.Int
		rsa_key_size: DF.Literal["2048", "3072", "4096"]
		status: DF.Literal["Pending", "Active", "Expired", "Revoked", "Failure"]
		team: DF.Link | None
		wildcard: DF.Check
	# end: auto-generated types

	def autoname(self):
		if self.wildcard:
			self.name = f"*.{self.domain}"
		else:
			self.name = self.domain

	def after_insert(self):
		self.obtain_certificate()

	def validate(self):
		if self.provider == "Other":
			if not self.team:
				frappe.throw("Team is mandatory for custom TLS certificates.")

			self.configure_full_chain()
			self.validate_key_length()
			self.validate_key_certificate_association()
			self._extract_certificate_details()

	def on_update(self):
		if self.is_new():
			return

		if self.has_value_changed("rsa_key_size"):
			self.obtain_certificate()

	@frappe.whitelist()
	def obtain_certificate(self):
		if self.provider != "Let's Encrypt":
			return

		if self.retry_count >= MANUAL_RETRY_LIMIT:
			frappe.throw("Retry limit exceeded. Please check the error and try again.", TLSRetryLimitExceeded)
		(
			user,
			session_data,
			team,
		) = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(),
		)

		frappe.set_user(frappe.get_value("Team", team, "user"))
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_obtain_certificate",
			enqueue_after_commit=True,
			job_id=f"obtain_certificate:{self.name}",
			deduplicate=True,
		)
		frappe.set_user(user)
		frappe.session.data = session_data

	@frappe.whitelist()
	def _obtain_certificate(self):
		if self.provider != "Let's Encrypt":
			return
		try:
			settings = frappe.get_doc("Press Settings", "Press Settings")
			ca = LetsEncrypt(settings)
			(
				self.certificate,
				self.full_chain,
				self.intermediate_chain,
				self.private_key,
			) = ca.obtain(domain=self.domain, rsa_key_size=self.rsa_key_size, wildcard=self.wildcard)
			self._extract_certificate_details()
			self.status = "Active"
			self.retry_count = 0
			self.error = None
		except Exception as e:
			# If certbot is already running, retry after 5 seconds
			# TODO: Move this to a queue
			if hasattr(e, "output") and e.output:
				out = e.output.decode()
				if "Another instance of Certbot is already running" in out:
					time.sleep(5)
					frappe.enqueue_doc(
						self.doctype,
						self.name,
						"_obtain_certificate",
						job_id=f"obtain_certificate:{self.name}",
						deduplicate=True,
					)
					return
				if re.search(r"Detail: .*: Invalid response", out):
					self.error = "Suggestion: You may have updated your DNS records recently. Please wait for the changes to propagate. Please try fetching certificate after some time."
					self.error += "\n" + out
				else:
					self.error = out
			else:
				self.error = repr(e)
			self.retry_count += 1
			self.status = "Failure"
			log_error("TLS Certificate Exception", certificate=self.name)
		self.save()
		self.trigger_site_domain_callback()
		self.trigger_self_hosted_server_callback()
		if self.wildcard:
			self.trigger_server_tls_setup_callback()
			self._update_secondary_wildcard_domains()
			self.setup_standalone_wildcard_hosts()

	def _update_secondary_wildcard_domains(self):
		"""
		Install secondary wildcard domains on proxies.

		Skip install on servers using the same domain for it's own hostname.
		"""
		proxies_containing_domain = frappe.get_all(
			"Proxy Server Domain", {"domain": self.domain}, pluck="parent"
		)
		proxies_using_domain = frappe.get_all("Proxy Server", {"domain": self.domain}, pluck="name")
		proxies_containing_domain = set(proxies_containing_domain) - set(proxies_using_domain)
		for proxy_name in proxies_containing_domain:
			proxy = frappe.get_doc("Proxy Server", proxy_name)
			proxy.setup_wildcard_hosts()

	@frappe.whitelist()
	def trigger_server_tls_setup_callback(self):
		server_doctypes = [
			"Proxy Server",
			"Server",
			"Database Server",
			"Log Server",
			"Monitor Server",
			"Registry Server",
			"Analytics Server",
			"Trace Server",
		]

		for server_doctype in server_doctypes:
			servers = frappe.get_all(
				server_doctype,
				filters={
					"status": ("not in", ["Archived", "Installing"]),
					"name": ("like", f"%.{self.domain}"),
				},
				fields=["name", "status"],
			)
			for server in servers:
				if server.status == "Active":
					frappe.enqueue(
						"press.press.doctype.tls_certificate.tls_certificate.update_server_tls_certifcate",
						server=frappe.get_doc(server_doctype, server.name),
						certificate=self,
						enqueue_after_commit=True,
					)
				else:
					# If server is not active, mark the tls_certificate_renewal_failed field as True
					frappe.db.set_value(
						server_doctype,
						server.name,
						"tls_certificate_renewal_failed",
						1,
						update_modified=False,
					)

	@frappe.whitelist()
	def trigger_site_domain_callback(self):
		domain = frappe.db.get_value("Site Domain", {"tls_certificate": self.name}, "name")
		if domain:
			frappe.get_doc("Site Domain", domain).process_tls_certificate_update()

	def trigger_self_hosted_server_callback(self):
		with suppress(Exception):
			frappe.get_doc("Self Hosted Server", self.name).process_tls_cert_update()

	def setup_standalone_wildcard_hosts(self):
		standalone_servers = frappe.get_all(
			"Server",
			filters={
				"status": ("not in", ["Archived", "Installing"]),
				"is_standalone_setup": 1,
			},
			pluck="name",
		)
		if standalone_servers:
			servers = frappe.get_all(
				"Site",
				filters={
					"status": ("!=", "Archived"),
					"domain": self.domain,
					"server": ("in", standalone_servers),
				},
				distinct=True,
				pluck="server",
			)

			for server in servers:
				frappe.get_doc("Server", server).setup_wildcard_hosts()

	def _extract_certificate_details(self):
		x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.certificate)
		self.decoded_certificate = OpenSSL.crypto.dump_certificate(
			OpenSSL.crypto.FILETYPE_TEXT, x509
		).decode()
		self.issued_on = datetime.strptime(x509.get_notBefore().decode(), "%Y%m%d%H%M%SZ")
		self.expires_on = datetime.strptime(x509.get_notAfter().decode(), "%Y%m%d%H%M%SZ")

	def configure_full_chain(self):
		if not self.full_chain:
			self.full_chain = f"{self.certificate}\n{self.intermediate_chain}"

	def _get_private_key_object(self):
		try:
			return OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, self.private_key)
		except OpenSSL.crypto.Error as e:
			log_error("TLS Private Key Exception", certificate=self.name)
			raise e

	def _get_certificate_object(self):
		try:
			return OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, self.full_chain)
		except OpenSSL.crypto.Error as e:
			log_error("Custom TLS Certificate Exception", certificate=self.name)
			raise e

	def validate_key_length(self):
		private_key = self._get_private_key_object()

		if private_key.bits() != int(self.rsa_key_size):
			frappe.throw(
				f"Private key length does not match the selected RSA key size. Expected {self.rsa_key_size} bits, got {private_key.bits()} bits."
			)

	def validate_key_certificate_association(self):
		context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
		context.use_privatekey(self._get_private_key_object())
		context.use_certificate(self._get_certificate_object())

		try:
			context.check_privatekey()
			self.status = "Active"
			self.retry_count = 0
			self.error = None
		except OpenSSL.SSL.Error as e:
			self.error = repr(e)
			log_error("TLS Key Certificate Association Exception", certificate=self.name)
			frappe.throw("Private Key and Certificate do not match")
		finally:
			if self.error:
				self.status = "Failure"


get_permission_query_conditions = get_permission_query_conditions_for_doctype("TLS Certificate")


class PendingCertificate(frappe._dict):
	name: str
	domain: str
	wildcard: bool
	retry_count: int


def should_renew(site: str | None, certificate: PendingCertificate) -> bool:
	if certificate.wildcard:
		return True
	if not site:
		return False
	if frappe.db.get_value("Site", site, "status") != "Active":
		return False
	dns_response = check_dns_cname_a(site, certificate.domain, ignore_proxying=True)
	if dns_response["matched"]:
		return True
	raise DNSValidationError(
		f"DNS check failed. {dns_response.get('answer')}",
	)


def rollback_and_fail_tls(certificate: PendingCertificate, e: Exception):
	frappe.db.rollback()
	frappe.db.set_value(
		"TLS Certificate",
		certificate.name,
		{
			"status": "Failure",
			"error": str(e),
			"retry_count": certificate.retry_count + 1,
		},
	)


def renew_tls_certificates():
	tls_renewal_queue_size = frappe.db.get_single_value("Press Settings", "tls_renewal_queue_size")
	pending = frappe.get_all(
		"TLS Certificate",
		fields=["name", "domain", "wildcard", "retry_count"],
		filters={
			"status": ("in", ("Active", "Failure")),
			"expires_on": ("<", frappe.utils.add_days(None, 25)),
			"retry_count": ("<", AUTO_RETRY_LIMIT),
			"provider": "Let's Encrypt",
		},
		ignore_ifnull=True,
		order_by="expires_on ASC, status DESC",  # Oldest first, then prefer failures.
	)
	renewals_attempted = 0
	for certificate in pending:
		if tls_renewal_queue_size and (renewals_attempted >= tls_renewal_queue_size):
			break

		site = frappe.db.get_value("Site Domain", {"tls_certificate": certificate.name}, "site")

		try:
			if not should_renew(site, certificate):
				continue
			renewals_attempted += 1
			certificate_doc = TLSCertificate("TLS Certificate", certificate.name)
			certificate_doc._obtain_certificate()
			frappe.db.commit()
		except DNSValidationError as e:
			rollback_and_fail_tls(certificate, e)  # has to come first as it has frappe.db.rollback()
			frappe.db.set_value(
				"Site Domain",
				{"tls_certificate": certificate.name},
				{"status": "Broken", "dns_response": str(e)},
			)
			frappe.db.commit()
		except Exception as e:
			rollback_and_fail_tls(certificate, e)
			log_error("TLS Renewal Exception", certificate=certificate, site=site)
			frappe.db.commit()


def notify_custom_tls_renewal():
	seven_days = frappe.utils.add_days(None, 7).date()
	fifteen_days = frappe.utils.add_days(None, 15).date()

	tls_cert = frappe.qb.DocType("TLS Certificate")

	# Notify team members 15 days and 7 days before expiry

	query = (
		frappe.qb.from_(tls_cert)
		.select(tls_cert.name, tls_cert.domain, tls_cert.team, tls_cert.expires_on)
		.where(tls_cert.status.isin(["Active", "Failure"]))
		.where((Date(tls_cert.expires_on) == seven_days) | (Date(tls_cert.expires_on) == fifteen_days))
		.where(tls_cert.provider == "Other")
	)

	pending = query.run(as_dict=True)

	for certificate in pending:
		if certificate.team:
			frappe.sendmail(
				recipients=get_communication_info("Email", "Site Activity", "Team", certificate.team),
				subject=f"TLS Certificate Renewal Required: {certificate.name}",
				message=f"TLS Certificate {certificate.name} is due for renewal on {certificate.expires_on}. Please renew the certificate to avoid service disruption.",
			)


def update_server_tls_certifcate(server, certificate):
	try:
		proxysql_admin_password = None
		if server.doctype == "Proxy Server":
			proxysql_admin_password = server.get_password("proxysql_admin_password")
		ansible = Ansible(
			playbook="tls.yml",
			user=server.get("ssh_user") or "root",
			port=server.get("ssh_port") or 22,
			server=server,
			variables={
				"certificate_private_key": certificate.private_key,
				"certificate_full_chain": certificate.full_chain,
				"certificate_intermediate_chain": certificate.intermediate_chain,
				"is_proxy_server": bool(proxysql_admin_password),
				"proxysql_admin_password": proxysql_admin_password,
			},
		)
		play: "AnsiblePlay" = ansible.run()
		frappe.db.set_value(
			server.doctype,
			server.name,
			"tls_certificate_renewal_failed",
			play.status != "Success",
			# to avoid causing TimestampMismatchError in other important tasks
			update_modified=False,
		)
	except Exception:
		log_error("TLS Setup Exception", server=server.as_dict())


def retrigger_failed_wildcard_tls_callbacks():
	server_doctypes = [
		"Proxy Server",
		"Server",
		"Database Server",
		"Log Server",
		"Monitor Server",
		"Registry Server",
		"Analytics Server",
		"Trace Server",
	]
	for server_doctype in server_doctypes:
		servers = frappe.get_all(
			server_doctype, filters={"status": "Active"}, fields=["name", "tls_certificate_renewal_failed"]
		)
		for server in servers:
			previous_attempt_failed = server.tls_certificate_renewal_failed
			if not previous_attempt_failed:
				plays = frappe.get_all(
					"Ansible Play",
					{"play": "Setup TLS Certificates", "server": server.name},
					pluck="status",
					limit=1,
					order_by="creation DESC",
				)
				if plays and plays[0] != "Success":
					previous_attempt_failed = True

			if previous_attempt_failed:
				server_doc = frappe.get_doc(server_doctype, server)
				frappe.enqueue(
					"press.press.doctype.tls_certificate.tls_certificate.update_server_tls_certifcate",
					server=server_doc,
					certificate=server_doc.get_certificate(),
				)


class BaseCA:
	def __init__(self, settings):
		self.settings = settings

	def obtain(self, domain, rsa_key_size=2048, wildcard=False):
		self.domain = f"*.{domain}" if wildcard else domain
		self.rsa_key_size = rsa_key_size
		self.wildcard = wildcard
		self._obtain()
		return self._extract()

	def _read_latest_certificate_file(self, file_path):
		import glob
		import os
		import re

		# Split path into directory and filename
		dir_path = os.path.dirname(file_path)
		file_name = os.path.basename(file_path)
		parent_dir = os.path.dirname(dir_path)
		base_dir_name = os.path.basename(dir_path)

		# Look for indexed directories first (e.g., dir-0000, dir-0001, etc.)
		indexed_dirs = glob.glob(os.path.join(parent_dir, f"{base_dir_name}-[0-9][0-9][0-9][0-9]"))

		if indexed_dirs:
			# Find directory with highest index
			latest_dir = max(indexed_dirs, key=lambda p: int(re.search(r"-(\d+)$", p).group(1)))
			latest_path = os.path.join(latest_dir, file_name)
		elif os.path.exists(file_path):
			latest_path = file_path
		else:
			raise FileNotFoundError(f"Certificate file not found: {file_path}")

		with open(latest_path) as f:
			return f.read()

	def _extract(self):
		certificate = self._read_latest_certificate_file(self.certificate_file)
		full_chain = self._read_latest_certificate_file(self.full_chain_file)
		intermediate_chain = self._read_latest_certificate_file(self.intermediate_chain_file)
		private_key = self._read_latest_certificate_file(self.private_key_file)
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
		environment = os.environ.copy()

		if(domain.dns_provider == 'AWS Route 53'):
			environment.update(
				{
					"AWS_ACCESS_KEY_ID": domain.aws_access_key_id,
					"AWS_SECRET_ACCESS_KEY": domain.get_password("aws_secret_access_key"),
				}
			)

		if domain.aws_region:
			environment["AWS_DEFAULT_REGION"] = domain.aws_region
		self.run(self._certbot_command(), environment=environment)

	def _obtain_naked_with_dns(self):
		domain = frappe.get_all("Root Domain", pluck="name", limit=1)[0]
		domain = frappe.get_doc("Root Domain", domain)
		environment = os.environ.copy()

		if(domain.dns_provider == 'AWS Route 53'):
			environment.update(
				{
					"AWS_ACCESS_KEY_ID": domain.aws_access_key_id,
					"AWS_SECRET_ACCESS_KEY": domain.get_password("aws_secret_access_key"),
				}
			)


	def _obtain_naked(self):
		if not os.path.exists(self.webroot_directory):
			os.mkdir(self.webroot_directory)
		self.run(self._certbot_command())

	def _certbot_command(self):
		domain = frappe.get_doc("Root Domain", self.domain[2:])
		if self.wildcard or frappe.conf.developer_mode:
			if(domain.dns_provider == 'AWS Route 53'):
				plugin = "--dns-route53"

			if(domain.dns_provider == 'Cloud Flare'):
				cloudflare_creds = os.path.join(self.directory, "cloudflare.ini")
				with open(cloudflare_creds, "w") as f:
					f.write(f"dns_cloudflare_api_token = {domain.get_password('cloud_flare_api_key')}")
				os.chmod(cloudflare_creds, 0o600)
				plugin = f"--dns-cloudflare --dns-cloudflare-credentials {cloudflare_creds}"
		else:
			plugin = f"--webroot --webroot-path {self.webroot_directory}"

		staging = "--staging" if self.staging else ""
		force_renewal = "--keep" if frappe.conf.developer_mode else "--force-renewal"

		return (
			f"certbot certonly {plugin} {staging} --logs-dir"
			f" {self.directory}/logs --work-dir {self.directory} --config-dir"
			f" {self.directory} {force_renewal} --agree-tos --eff-email --email"
			f" {self.eff_registration_email} --staple-ocsp"
			" --key-type rsa"
			f" --rsa-key-size {self.rsa_key_size} --cert-name {self.domain} --domains"
			f" {self.domain}"
		)

	def run(self, command, environment=None):
		try:
			subprocess.check_output(shlex.split(command), stderr=subprocess.STDOUT, env=environment)
		except subprocess.CalledProcessError as e:
			output = (e.output or b"").decode()
			if "Another instance of Certbot is already running" not in output:
				log_error("Certbot Exception", command=command, output=output)
			raise e
		except Exception as e:
			log_error("Certbot Exception", command=command, exception=e)
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
