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
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import frappe
import requests

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class UnreachableURLError(frappe.ValidationError):
	pass


def fetch_public_url(url: str) -> str:
	"""GET a user-supplied URL and return its body, refusing anything internal."""
	for _ in range(MAX_REDIRECTS + 1):
		validate_public_url(url)
		response = requests.get(
			url,
			timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
			allow_redirects=False,
			stream=True,
		)

		if not response.is_redirect:
			return read_capped_body(response)

		url = urljoin(url, response.headers["Location"])

	frappe.throw(f"{url} redirected more than {MAX_REDIRECTS} times", UnreachableURLError)
	raise  # for mypy: NoReturn


def validate_public_url(url: str):
	"""Refuse a URL that names anything other than a host out on the internet."""
	parsed = urlparse(url)

	if parsed.scheme not in ("http", "https"):
		frappe.throw(f"{url} must be an http:// or https:// URL", UnreachableURLError)

	if not parsed.hostname:
		frappe.throw(f"{url} names no host to fetch from", UnreachableURLError)
		raise  # for mypy: NoReturn

	for address in resolved_addresses(parsed.hostname):
		if not address.is_global:
			frappe.throw(
				f"{parsed.hostname} resolves to {address}, which is on our network rather than the internet",
				UnreachableURLError,
			)


def resolved_addresses(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
	"""Every address the host resolves to. All of them have to be public."""
	try:
		infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
	except socket.gaierror:
		frappe.throw(f"{hostname} could not be resolved", UnreachableURLError)
		raise  # for mypy: NoReturn

	return [unmapped(ipaddress.ip_address(info[4][0])) for info in infos]


def unmapped(address):
	"""An IPv4 address written as IPv6 is still that IPv4 address."""
	if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
		return address.ipv4_mapped

	return address


def read_capped_body(response: requests.Response) -> str:
	response.raise_for_status()

	body = b""
	for chunk in response.iter_content(chunk_size=8192):
		body += chunk
		if len(body) > MAX_RESPONSE_BYTES:
			frappe.throw(f"{response.url} returned more than {MAX_RESPONSE_BYTES} bytes", UnreachableURLError)

	return body.decode(response.encoding or "utf-8", errors="replace")
