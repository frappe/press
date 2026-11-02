# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import socket
from unittest.mock import patch

import requests
from frappe.tests.utils import FrappeTestCase

from press.utils import ssrf


def resolve_to(*ips):
	"""Fake socket.getaddrinfo that resolves any host to `ips`."""
	return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in ips]


def resolve_by_host(hosts: dict[str, str]):
	"""Fake socket.getaddrinfo that resolves each host in `hosts` to its IP."""
	return lambda hostname, *args, **kwargs: resolve_to(hosts[hostname])


def fake_responses(*responses: tuple[int, str | None]):
	"""Fake HTTPAdapter.send that answers with (status, Location) in turn, and records the Host of each request."""
	hosts = []
	queue = list(responses)

	def send(self, request, **kwargs):
		hosts.append(request.headers["Host"])
		status, location = queue.pop(0)
		response = requests.Response()
		response.status_code = status
		if location:
			response.headers["Location"] = location
		return response

	return send, hosts


class TestSSRF(FrappeTestCase):
	def test_public_hostname_resolves_to_its_ip(self):
		with patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("93.184.216.34")):
			self.assertEqual(ssrf._resolve_public_ip("example.com"), "93.184.216.34")

	def test_dual_stack_hostname_resolves_to_its_ipv4_address(self):
		with patch(
			"press.utils.ssrf.socket.getaddrinfo",
			return_value=resolve_to("2606:4700::6810:84e5", "104.16.132.229"),
		):
			self.assertEqual(ssrf._resolve_public_ip("worker.workers.dev"), "104.16.132.229")

	def test_ipv6_only_hostname_resolves_to_its_ipv6_address(self):
		with patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("2606:4700::6810:84e5")):
			self.assertEqual(ssrf._resolve_public_ip("ipv6.example.com"), "2606:4700::6810:84e5")

	def test_hostname_resolving_to_metadata_ip_is_rejected(self):
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("169.254.169.254")),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf._resolve_public_ip("metadata.attacker.com")

	def test_hostname_resolving_to_private_range_is_rejected(self):
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("10.0.0.5")),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf._resolve_public_ip("internal.attacker.com")

	def test_hostname_with_any_private_record_is_rejected(self):
		# DNS rebinding via mixed A records: one private answer fails the whole resolve.
		with (
			patch(
				"press.utils.ssrf.socket.getaddrinfo",
				return_value=resolve_to("93.184.216.34", "127.0.0.1"),
			),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf._resolve_public_ip("rebind.attacker.com")

	def test_ipv4_mapped_ipv6_loopback_is_rejected(self):
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("::ffff:127.0.0.1")),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf._resolve_public_ip("mapped.attacker.com")

	def test_unresolvable_host_is_rejected(self):
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", side_effect=socket.gaierror),
			self.assertRaisesRegex(ssrf.SSRFError, "Could not resolve"),
		):
			ssrf._resolve_public_ip("does-not-exist.invalid")

	def test_post_to_private_endpoint_raises_before_any_connection(self):
		# The request must be refused at resolution; requests.Session.post is never reached.
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("169.254.169.254")),
			patch("requests.Session.post") as post,
		):
			with self.assertRaises(ssrf.SSRFError):
				ssrf.post("http://metadata.attacker.com/latest/meta-data/", timeout=5)
			post.assert_not_called()

	def test_post_to_url_without_host_is_rejected(self):
		with self.assertRaisesRegex(ssrf.SSRFError, "no host"):
			ssrf.post("/latest/meta-data/", timeout=5)

	def test_basic_auth_url_keeps_credentials_out_of_host_header(self):
		# user:password@host must land in the Authorization header, never in Host,
		# and the request must still be pinned to the resolved IP.
		captured = {}

		def capture(self, request, **kwargs):
			captured["host"] = request.headers.get("Host")
			captured["authorization"] = request.headers.get("Authorization")
			captured["url"] = request.url
			response = requests.Response()
			response.status_code = 200
			return response

		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("93.184.216.34")),
			patch("requests.adapters.HTTPAdapter.send", capture),
		):
			ssrf.post("http://user:password@example.com:8080/hook", timeout=5)  # pragma: allowlist secret

		self.assertEqual(captured["host"], "example.com:8080")
		self.assertTrue(captured["authorization"].startswith("Basic "))
		self.assertTrue(captured["url"].startswith("http://93.184.216.34:8080/"))

	def test_get_follows_redirect_to_public_host_and_reports_final_url(self):
		send, hosts = fake_responses((301, "https://www.example.com/ping"), (200, None))
		with (
			patch(
				"press.utils.ssrf.socket.getaddrinfo",
				resolve_by_host({"example.com": "93.184.216.34", "www.example.com": "93.184.216.35"}),
			),
			patch("requests.adapters.HTTPAdapter.send", send),
		):
			response = ssrf.get("http://example.com/ping")

		self.assertEqual(hosts, ["example.com", "www.example.com"])
		self.assertEqual(response.url, "https://www.example.com/ping")

	def test_get_refuses_redirect_that_fails_the_check_before_requesting_it(self):
		send, hosts = fake_responses((302, "http://files.example.com/"), (200, None))
		with (
			patch(
				"press.utils.ssrf.socket.getaddrinfo",
				resolve_by_host({"example.com": "93.184.216.34", "files.example.com": "10.0.0.5"}),
			),
			patch("requests.adapters.HTTPAdapter.send", send),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf.get("http://example.com/ping")

		self.assertEqual(hosts, ["example.com"])

	def test_head_gives_up_after_too_many_redirects(self):
		send, hosts = fake_responses(*[(302, "/again")] * (ssrf.MAX_REDIRECTS + 1))
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("93.184.216.34")),
			patch("requests.adapters.HTTPAdapter.send", send),
			self.assertRaisesRegex(ssrf.SSRFError, "redirects too many times"),
		):
			ssrf.head("http://example.com/backup.sql.gz")

		self.assertEqual(len(hosts), ssrf.MAX_REDIRECTS + 1)

	def test_validate_rejects_url_that_is_not_http(self):
		for url in ("file:///tmp/config.json", "ftp://example.com/config.json"):
			with self.subTest(url=url), self.assertRaisesRegex(ssrf.SSRFError, "http and https"):
				ssrf.validate(url)

	def test_validate_rejects_url_that_fails_the_address_check(self):
		with (
			patch("press.utils.ssrf.socket.getaddrinfo", return_value=resolve_to("127.0.0.1")),
			self.assertRaisesRegex(ssrf.SSRFError, "private or internal"),
		):
			ssrf.validate("http://files.example.com")
