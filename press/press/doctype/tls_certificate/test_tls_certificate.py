# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import unittest
from typing import Literal
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.tls_certificate.tls_certificate import (
	BaseCA,
	LetsEncrypt,
	TLSCertificate,
)


@patch.object(TLSCertificate, "obtain_certificate", new=Mock())
def create_test_tls_certificate(
	domain: str, wildcard: bool = False, provider: Literal["Let's Encrypt", "Other"] = "Let's Encrypt"
) -> TLSCertificate:
	certificate = frappe.get_doc(
		{
			"doctype": "TLS Certificate",
			"domain": domain,
			"rsa_key_size": 2048,
			"wildcard": wildcard,
			"provider": provider,
		}
	).insert(ignore_if_duplicate=True)
	certificate.reload()
	return certificate


def none_init(self, settings):
	pass


def fake_extract(self):
	return "a", "b", "c", "d"


@patch.object(AgentJob, "after_insert", new=Mock())
@patch.object(LetsEncrypt, "_obtain", new=Mock())
@patch.object(BaseCA, "_extract", new=fake_extract)
@patch.object(TLSCertificate, "_extract_certificate_details", new=Mock())
class TestTLSCertificate(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_renewal_of_secondary_wildcard_domains_updates_server(self):
		erpnext_domain = create_test_root_domain("erpnext.xyz")
		fc_domain = create_test_root_domain("fc.dev")
		create_test_proxy_server(  # creates n1.fc.dev by default
			"n1", domains=[{"domain": fc_domain.name}, {"domain": erpnext_domain.name}]
		)

		cert = create_test_tls_certificate(erpnext_domain.name, wildcard=True)

		with patch.object(LetsEncrypt, "__init__", new=none_init), patch.object(
			ProxyServer, "setup_wildcard_hosts"
		) as mock_setup_wildcard_hosts:
			cert._obtain_certificate()
		mock_setup_wildcard_hosts.assert_called_once()

	def test_renewal_of_primary_wildcard_domains_doesnt_call_setup_wildcard_domains(self):
		erpnext_domain = create_test_root_domain("erpnext.xyz")
		fc_domain = create_test_root_domain("fc.dev")
		create_test_proxy_server("n1", domains=[{"domain": fc_domain.name}, {"domain": erpnext_domain.name}])

		cert = create_test_tls_certificate(fc_domain.name, wildcard=True)
		cert.reload()  # already created with proxy server

		with patch.object(LetsEncrypt, "__init__", new=none_init), patch.object(
			TLSCertificate, "trigger_server_tls_setup_callback", new=Mock()
		), patch.object(ProxyServer, "setup_wildcard_hosts") as mock_setup_wildcard_hosts:
			cert._obtain_certificate()

		mock_setup_wildcard_hosts.assert_not_called()

	def test_renewal_of_primary_domain_calls_update_tls_certificates(self):
		# Use a diffferent domain to avoid any chance of
		# Reusing same non wildcard domain in tests
		# Because, in create_test_tls_certificate, we ignore certificate creation if it already exists
		create_test_root_domain("fc2.dev")
		cert = create_test_tls_certificate("fc2.dev", wildcard=True)
		create_test_proxy_server("n2", domain="fc2.dev")
		with patch.object(LetsEncrypt, "__init__", new=none_init), patch.object(
			TLSCertificate, "trigger_server_tls_setup_callback"
		) as mock_trigger_server_tls_setup, patch.object(ProxyServer, "setup_wildcard_hosts", new=Mock()):
			cert._obtain_certificate()
		mock_trigger_server_tls_setup.assert_called()
