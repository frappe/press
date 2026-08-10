# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import socket
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.external_url import UnreachableURLError, fetch_public_url, validate_public_url


def answer(*addresses: str):
	return [(None, None, None, None, (address, 0)) for address in addresses]


def resolving_to(*addresses: str):
	"""Stand in for DNS so the tests never depend on a real lookup."""
	return patch("press.utils.external_url.socket.getaddrinfo", return_value=answer(*addresses))


def resolving_in_turn(*answers: list):
	"""DNS answering differently for each host looked up, in order."""
	return patch("press.utils.external_url.socket.getaddrinfo", side_effect=list(answers))


class TestValidatePublicURL(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_public_address_is_accepted(self):
		with resolving_to("93.184.216.34"):
			validate_public_url("https://example.com/some.patch")

	def test_link_local_metadata_address_is_refused(self):
		with resolving_to("169.254.169.254"), self.assertRaises(UnreachableURLError) as caught:
			validate_public_url("http://169.254.169.254/metadata/v1.json")

		self.assertIn("on our network rather than the internet", str(caught.exception))

	def test_loopback_address_is_refused(self):
		with resolving_to("127.0.0.1"), self.assertRaises(UnreachableURLError):
			validate_public_url("http://localhost/agent")

	def test_private_address_is_refused(self):
		with resolving_to("10.0.0.5"), self.assertRaises(UnreachableURLError):
			validate_public_url("https://internal.frappe.cloud/")

	def test_host_resolving_to_both_public_and_private_is_refused(self):
		with resolving_to("93.184.216.34", "10.0.0.5"), self.assertRaises(UnreachableURLError):
			validate_public_url("https://split-horizon.example.com/")

	def test_ipv4_mapped_ipv6_metadata_address_is_refused(self):
		with resolving_to("::ffff:169.254.169.254"), self.assertRaises(UnreachableURLError):
			validate_public_url("https://sneaky.example.com/")

	def test_non_http_scheme_is_refused(self):
		with self.assertRaises(UnreachableURLError) as caught:
			validate_public_url("file:///etc/passwd")

		self.assertIn("must be an http:// or https:// URL", str(caught.exception))

	def test_url_without_a_host_is_refused(self):
		with self.assertRaises(UnreachableURLError) as caught:
			validate_public_url("http:///nowhere")

		self.assertIn("names no host to fetch from", str(caught.exception))

	def test_unresolvable_host_is_refused(self):
		with (
			patch("press.utils.external_url.socket.getaddrinfo", side_effect=socket.gaierror),
			self.assertRaises(UnreachableURLError) as caught,
		):
			validate_public_url("https://no-such-host.example/")

		self.assertIn("could not be resolved", str(caught.exception))


class TestFetchPublicURL(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_redirect_to_an_internal_address_is_refused(self):
		"""A public host is free to redirect at the metadata service."""
		redirect = frappe._dict(
			is_redirect=True,
			headers={"Location": "http://169.254.169.254/metadata/v1.json"},
		)

		with (
			resolving_in_turn(answer("93.184.216.34"), answer("169.254.169.254")),
			patch("press.utils.external_url.requests.get", return_value=redirect),
			self.assertRaises(UnreachableURLError) as caught,
		):
			fetch_public_url("https://example.com/redirects.patch")

		self.assertIn("169.254.169.254", str(caught.exception))

	def test_body_is_returned_when_every_hop_is_public(self):
		response = frappe._dict(
			is_redirect=False,
			encoding="utf-8",
			raise_for_status=lambda: None,
			iter_content=lambda chunk_size: [b"diff --git a/x b/x"],
		)

		with (
			resolving_to("93.184.216.34"),
			patch("press.utils.external_url.requests.get", return_value=response),
		):
			self.assertEqual(fetch_public_url("https://example.com/x.patch"), "diff --git a/x b/x")
