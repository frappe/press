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
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter


class SSRFError(Exception):
	"""The webhook endpoint points at a private, internal, or unresolvable address."""


def post(url: str, **kwargs) -> requests.Response:
	"""POST to a customer-controlled `url`, refusing any non-public target."""
	parts = urlsplit(url)
	if not parts.hostname:
		raise SSRFError("The endpoint URL has no host.")
	ip = _resolve_public_ip(parts.hostname)
	kwargs["allow_redirects"] = False
	with requests.Session() as session:
		session.mount(f"{parts.scheme}://", _PinnedIPAdapter(ip, parts.hostname))
		return session.post(url, **kwargs)


def _resolve_public_ip(hostname: str) -> str:
	"""Resolve `hostname`, refusing if any address it maps to is not global."""
	try:
		addresses = socket.getaddrinfo(hostname, None)
	except socket.gaierror as error:
		raise SSRFError(f"Could not resolve the endpoint host '{hostname}'.") from error

	ips = {str(address[4][0]) for address in addresses}
	for ip in ips:
		if not _is_public(ip):
			raise SSRFError("The endpoint resolves to a private or internal address, which is not allowed.")
	return next(iter(ips))


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
