# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.tls_certificate.tls_certificate import (
	LetsEncrypt,
	TLSCertificate,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from unittest.mock import Mock, patch
from press.press.doctype.agent_job.agent_job import AgentJob

import frappe
import unittest


@patch.object(TLSCertificate, "obtain_certificate", new=Mock())
def create_test_tls_certificate(domain: str, wildcard: bool = False):
	return frappe.get_doc(
		{
			"doctype": "TLS Certificate",
			"domain": domain,
			"rsa_key_size": 2048,
			"wildcard": wildcard,
		}
	).insert(ignore_if_duplicate=True)


@patch.object(AgentJob, "after_insert", new=Mock())
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

		with patch.object(LetsEncrypt, "obtain", new=Mock()), patch.object(
			LetsEncrypt, "__init__", new=Mock()
		), patch.object(
			ProxyServer, "setup_wildcard_hosts"
		) as mock_setup_wildcard_hosts:
			cert._obtain_certificate()
		mock_setup_wildcard_hosts.assert_called_once()

	def test_renewal_of_primary_wildcard_domains_doesnt_call_setup_wildcard_domains(self):
		erpnext_domain = create_test_root_domain("erpnext.xyz")
		fc_domain = create_test_root_domain("fc.dev")
		create_test_proxy_server(
			"n1", domains=[{"domain": fc_domain.name}, {"domain": erpnext_domain.name}]
		)

		cert = create_test_tls_certificate(fc_domain.name, wildcard=True)
		cert.reload()  # already created with proxy server

		with patch.object(LetsEncrypt, "obtain", new=Mock()), patch.object(
			LetsEncrypt, "__init__", new=Mock()
		), patch.object(
			TLSCertificate, "trigger_server_tls_setup_callback", new=Mock()
		), patch.object(
			ProxyServer, "setup_wildcard_hosts"
		) as mock_setup_wildcard_hosts:
			cert._obtain_certificate()

		mock_setup_wildcard_hosts.assert_not_called()

	def test_renewal_of_primary_domain_calls_update_tls_certificates(self):
		cert = create_test_tls_certificate("fc.dev", wildcard=True)
		create_test_proxy_server("n1")
		with patch.object(LetsEncrypt, "obtain", new=Mock()), patch.object(
			LetsEncrypt, "__init__", new=Mock()
		), patch.object(
			TLSCertificate, "trigger_server_tls_setup_callback"
		) as mock_trigger_server_tls_setup, patch.object(
			ProxyServer, "setup_wildcard_hosts", new=Mock()
		):
			cert._obtain_certificate()
		mock_trigger_server_tls_setup.assert_called()
