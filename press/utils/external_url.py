# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Fetching a URL that a user typed in.

Press runs inside the cloud account that owns every server it manages, so a
plain `requests.get` on a user-supplied URL reads whatever that network can
reach — the instance metadata service on 169.254.169.254 first among them, and
the response comes back to the user who asked for it.

`fetch_public_url` resolves the host and refuses every address that is not
globally routable. It does this again for each redirect it follows, because a
public host is free to redirect to a private one.

Checking a name and then handing that same name to `requests` would resolve it
twice, and a name under someone else's control is free to answer publicly the
first time and privately the second. So the address that passed the check is
the address dialled; the hostname survives only in the `Host` header and the
TLS handshake, which is what `server_hostname` is for.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import frappe
import requests
from requests.adapters import HTTPAdapter

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 10 * 1024 * 1024

Address = ipaddress.IPv4Address | ipaddress.IPv6Address


class UnreachableURLError(frappe.ValidationError):
	pass


class PinnedHostAdapter(HTTPAdapter):
	"""Verifies the certificate against the name asked for, not the address dialled."""

	def __init__(self, hostname: str):
		self.hostname = hostname
		super().__init__()

	def init_poolmanager(self, *args, **kwargs):
		kwargs["server_hostname"] = self.hostname
		kwargs["assert_hostname"] = self.hostname
		super().init_poolmanager(*args, **kwargs)


def fetch_public_url(url: str) -> str:
	"""GET a user-supplied URL and return its body, refusing anything internal."""
	with requests.Session() as session:
		for _ in range(MAX_REDIRECTS + 1):
			response = get_pinned(session, url)

			if not response.is_redirect:
				return read_capped_body(response, url)

			url = urljoin(url, response.headers["Location"])

	frappe.throw(f"{url} redirected more than {MAX_REDIRECTS} times", UnreachableURLError)
	raise  # for mypy: NoReturn


def get_pinned(session: requests.Session, url: str) -> requests.Response:
	"""GET the address that passed the check, still speaking to the host by name."""
	hostname, address = validate_public_url(url)
	parsed = urlparse(url)

	session.mount("https://", PinnedHostAdapter(hostname))
	return session.get(
		urlunparse(parsed._replace(netloc=dialled_netloc(address, parsed.port))),
		headers={"Host": parsed.netloc.rsplit("@", 1)[-1]},
		timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
		allow_redirects=False,
		stream=True,
	)


def dialled_netloc(address: Address, port: int | None) -> str:
	host = f"[{address}]" if isinstance(address, ipaddress.IPv6Address) else str(address)
	return f"{host}:{port}" if port else host


def validate_public_url(url: str) -> tuple[str, Address]:
	"""Refuse a URL naming anything but a host out on the internet.

	Returns the hostname and the address to dial. Every address the name
	resolves to has to be public, so any of them will do.
	"""
	parsed = urlparse(url)

	if parsed.scheme not in ("http", "https"):
		frappe.throw(f"{url} must be an http:// or https:// URL", UnreachableURLError)

	if not parsed.hostname:
		frappe.throw(f"{url} names no host to fetch from", UnreachableURLError)
		raise  # for mypy: NoReturn

	addresses = resolved_addresses(parsed.hostname)
	for address in addresses:
		if not address.is_global:
			frappe.throw(
				f"{parsed.hostname} resolves to {address}, which is on our network rather than the internet",
				UnreachableURLError,
			)

	return parsed.hostname, addresses[0]


def resolved_addresses(hostname: str) -> list[Address]:
	"""Every address the host resolves to. All of them have to be public."""
	try:
		infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
	except socket.gaierror:
		frappe.throw(f"{hostname} could not be resolved", UnreachableURLError)
		raise  # for mypy: NoReturn

	if not infos:
		frappe.throw(f"{hostname} resolves to no addresses", UnreachableURLError)

	return [unmapped(ipaddress.ip_address(info[4][0])) for info in infos]


def unmapped(address):
	"""An IPv4 address written as IPv6 is still that IPv4 address."""
	if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
		return address.ipv4_mapped

	return address


def read_capped_body(response: requests.Response, url: str) -> str:
	"""`url` is the one the caller asked for; `response.url` names the pinned address."""
	response.raise_for_status()

	body = b""
	for chunk in response.iter_content(chunk_size=8192):
		body += chunk
		if len(body) > MAX_RESPONSE_BYTES:
			frappe.throw(f"{url} returned more than {MAX_RESPONSE_BYTES} bytes", UnreachableURLError)

	return body.decode(response.encoding or "utf-8", errors="replace")
