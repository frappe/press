"""Security helpers for persisted Ansible execution metadata."""

import base64
import ipaddress
import os
import tempfile
from collections.abc import Mapping


_SENSITIVE_KEY_MARKERS = (
	"password",
	"secret",
	"token",
	"private_key",
	"privatekey",
	"api_key",
	"access_key",
)
_SENSITIVE_EXACT_KEYS = {"ssh_keys"}


def redact_ansible_secrets(value):
	"""Return a recursively redacted copy, leaving execution inputs untouched."""
	if isinstance(value, Mapping):
		redacted = {}
		for key, item in value.items():
			normalized_key = str(key).lower().replace("-", "_")
			if normalized_key in _SENSITIVE_EXACT_KEYS or any(
				marker in normalized_key for marker in _SENSITIVE_KEY_MARKERS
			):
				redacted[key] = "[REDACTED]"
			else:
				redacted[key] = redact_ansible_secrets(item)
		return redacted
	if isinstance(value, list):
		return [redact_ansible_secrets(item) for item in value]
	if isinstance(value, tuple):
		return tuple(redact_ansible_secrets(item) for item in value)
	return value


def build_only_ssh_host_variables(server, host, *, port=22, directory=None):
	"""Create a short-lived, pinned known_hosts file for build-only SSH provisioning."""
	if not getattr(server, "is_build_only", False):
		return {}, None

	try:
		ssh_ip = ipaddress.ip_address(host)
		tailnet = ipaddress.ip_network("100.64.0.0/10")
	except ValueError:
		raise ValueError("Build-only SSH must target a Tailnet IPv4 address") from None
	if ssh_ip.version != 4 or ssh_ip not in tailnet:
		raise ValueError("Build-only SSH must target a Tailnet IPv4 address")

	key_parts = (getattr(server, "build_ssh_host_public_key", None) or "").strip().split()
	if len(key_parts) != 2:
		raise ValueError("Build-only SSH requires a verified host public key")

	key_type, key_data = key_parts
	if any(character in key_type + key_data for character in "\r\n\x00"):
		raise ValueError("Build-only SSH host public key is malformed")
	try:
		key_blob = base64.b64decode(key_data, validate=True)
		key_type_length = int.from_bytes(key_blob[:4], "big")
		embedded_type = key_blob[4 : 4 + key_type_length].decode("ascii")
	except (ValueError, UnicodeDecodeError):
		raise ValueError("Build-only SSH host public key is malformed") from None
	if embedded_type != key_type or len(key_blob) <= 4 + key_type_length:
		raise ValueError("Build-only SSH host public key is malformed")

	host_entry = host if port == 22 else f"[{host}]:{port}"
	file_descriptor, path = tempfile.mkstemp(prefix="press-build-only-known-hosts-", dir=directory)
	try:
		os.fchmod(file_descriptor, 0o600)
		with os.fdopen(file_descriptor, "w", encoding="utf-8") as known_hosts:
			known_hosts.write(f"{host_entry} {key_type} {key_data}\n")
	except Exception:
		os.unlink(path)
		raise

	return {
		"ansible_ssh_host_key_checking": True,
		"ansible_ssh_common_args": (
			f"-o StrictHostKeyChecking=yes -o UserKnownHostsFile={path} "
			f"-o GlobalKnownHostsFile=/dev/null"
		),
	}, path
