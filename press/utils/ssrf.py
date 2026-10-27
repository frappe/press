# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

"""Send outbound webhook requests without letting them reach internal hosts.

A customer controls the webhook endpoint, and Press — the control plane — is
what makes the request. An unguarded request can be pointed at the cloud
metadata service (169.254.169.254), localhost, or a private range, turning
Press into a proxy that fetches internal resources and hands the response back.

We resolve the host ourselves and refuse any address that is not globally
routable, pin the connection to that address so the name cannot be re-pointed
between the check and the connect (DNS rebinding), and never follow redirects
so a public endpoint cannot bounce us inward.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter

MAX_REDIRECTS = 3
DEFAULT_TIMEOUT = (5, 10)


class SSRFError(Exception):
	"""The webhook endpoint points at a private, internal, or unresolvable address."""


def get(url: str, **kwargs) -> requests.Response:
	"""GET a customer-controlled `url`, refusing any non-public target or redirect."""
	return _follow_redirects("GET", url, **kwargs)


def head(url: str, **kwargs) -> requests.Response:
	"""HEAD a customer-controlled `url`, refusing any non-public target or redirect."""
	return _follow_redirects("HEAD", url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
	"""POST to a customer-controlled `url`, refusing any non-public target. Never redirects."""
	return _send("POST", url, **kwargs)


def validate(url: str):
	"""Refuse `url` unless it is http(s) and its host resolves to public addresses only."""
	_resolve_public_ip(_hostname(url))


def _follow_redirects(method: str, url: str, **kwargs) -> requests.Response:
	"""Follow up to MAX_REDIRECTS redirects, and check each target like the first URL."""
	for _ in range(MAX_REDIRECTS + 1):
		response = _send(method, url, **kwargs)
		if not response.is_redirect:
			return response
		url = urljoin(url, response.headers["Location"])
	raise SSRFError("The URL redirects too many times.")


def _send(method: str, url: str, **kwargs) -> requests.Response:
	hostname = _hostname(url)
	ip = _resolve_public_ip(hostname)
	kwargs["allow_redirects"] = False
	kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
	with requests.Session() as session:
		session.mount(f"{urlsplit(url).scheme}://", _PinnedIPAdapter(ip, hostname))
		response = session.request(method, url, **kwargs)
	# The adapter rewrites the URL to the pinned IP. Callers expect the URL they asked for.
	response.url = url
	return response


def _hostname(url: str) -> str:
	parts = urlsplit(url)
	if parts.scheme and parts.scheme not in ("http", "https"):
		raise SSRFError("Only http and https URLs are allowed.")
	if not parts.hostname:
		raise SSRFError("The endpoint URL has no host.")
	return parts.hostname


def _resolve_public_ip(hostname: str) -> str:
	"""Resolve `hostname`, refusing if any address it maps to is not global."""
	try:
		addresses = socket.getaddrinfo(hostname, None)
	except socket.gaierror as error:
		raise SSRFError(f"Could not resolve the endpoint host '{hostname}'.") from error

	ips = [str(address[4][0]) for address in addresses]
	for ip in ips:
		if not _is_public(ip):
			raise SSRFError("The endpoint resolves to a private or internal address, which is not allowed.")
	return _prefer_ipv4(ips)


def _prefer_ipv4(ips: list[str]) -> str:
	"""Pick an IPv4 address when the host is dual-stack, as the control plane may lack IPv6 egress."""
	return next((ip for ip in ips if ipaddress.ip_address(ip).version == 4), ips[0])


def _is_public(ip: str) -> bool:
	address = ipaddress.ip_address(ip)
	if address.version == 6 and address.ipv4_mapped:
		address = address.ipv4_mapped
	return address.is_global


def _authority(host: str, port: int | None) -> str:
	"""Format host and port as a URL authority, bracketing an IPv6 literal."""
	host = f"[{host}]" if ":" in host else host
	return f"{host}:{port}" if port else host


class _PinnedIPAdapter(HTTPAdapter):
	"""Connect to a pre-validated IP while keeping the Host header and the TLS
	certificate check bound to the original hostname, so the name cannot resolve
	to an internal address between the check and the connect (DNS rebinding)."""

	def __init__(self, ip: str, hostname: str, **kwargs):
		self.ip = ip
		self.hostname = hostname
		self.is_https = False
		super().__init__(**kwargs)

	def send(self, request, **kwargs):
		parts = urlsplit(request.url)
		self.is_https = parts.scheme == "https"
		# Build both authorities from host and port only. parts.netloc can carry
		# userinfo (user:password@host), which must not leak into the Host header.
		request.headers["Host"] = _authority(parts.hostname, parts.port)
		request.url = urlunsplit(parts._replace(netloc=_authority(self.ip, parts.port)))
		return super().send(request, **kwargs)

	def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
		return self._pin(super().get_connection_with_tls_context(request, verify, proxies, cert))

	def get_connection(self, url, proxies=None):
		return self._pin(super().get_connection(url, proxies))

	def _pin(self, pool):
		"""Point TLS at the original hostname on a pool that connects to the IP."""
		if self.is_https:
			pool.assert_hostname = self.hostname
			pool.conn_kw["server_hostname"] = self.hostname
		return pool
