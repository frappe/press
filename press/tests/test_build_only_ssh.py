import base64
import os
import stat
import tempfile
from types import SimpleNamespace
from unittest import TestCase

from press.ansible_security import build_only_ssh_host_variables, redact_ansible_secrets


def _test_ed25519_host_key():
	key_type = b"ssh-ed25519"
	key_blob = len(key_type).to_bytes(4, "big") + key_type + (32).to_bytes(4, "big") + b"x" * 32
	return f"ssh-ed25519 {base64.b64encode(key_blob).decode()}"


class TestBuildOnlySSHHostKeyChecking(TestCase):
	def test_build_only_ssh_uses_pinned_host_key_and_private_temporary_file(self):
		server = SimpleNamespace(
			is_build_only=True,
			build_ssh_host_public_key=_test_ed25519_host_key(),
		)
		with tempfile.TemporaryDirectory() as directory:
			settings, path = build_only_ssh_host_variables(
				server, "100.106.180.55", directory=directory
			)
			with open(path, encoding="utf-8") as known_hosts:
				self.assertEqual(
					known_hosts.read(), f"100.106.180.55 {_test_ed25519_host_key()}\n"
				)
			self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
			self.assertTrue(settings["ansible_ssh_host_key_checking"])
			self.assertIn("StrictHostKeyChecking=yes", settings["ansible_ssh_common_args"])
			self.assertIn(f"UserKnownHostsFile={path}", settings["ansible_ssh_common_args"])
			self.assertIn("GlobalKnownHostsFile=/dev/null", settings["ansible_ssh_common_args"])
			os.unlink(path)

	def test_non_default_ssh_port_uses_bracketed_known_hosts_entry(self):
		server = SimpleNamespace(
			is_build_only=True,
			build_ssh_host_public_key=_test_ed25519_host_key(),
		)
		with tempfile.TemporaryDirectory() as directory:
			_, path = build_only_ssh_host_variables(
				server, "100.106.180.55", port=2222, directory=directory
			)
			with open(path, encoding="utf-8") as known_hosts:
				self.assertTrue(known_hosts.read().startswith("[100.106.180.55]:2222 "))
			os.unlink(path)

	def test_malformed_pinned_key_is_rejected(self):
		server = SimpleNamespace(is_build_only=True, build_ssh_host_public_key="bad key\nother")
		with self.assertRaises(ValueError):
			build_only_ssh_host_variables(server, "100.106.180.55")

	def test_non_tailnet_host_is_rejected(self):
		server = SimpleNamespace(
			is_build_only=True,
			build_ssh_host_public_key=_test_ed25519_host_key(),
		)
		with self.assertRaises(ValueError):
			build_only_ssh_host_variables(server, "31.97.157.173")

	def test_existing_servers_keep_their_current_ssh_behavior(self):
		self.assertEqual(
			build_only_ssh_host_variables(SimpleNamespace(is_build_only=False), "host"), ({}, None)
		)
		self.assertEqual(build_only_ssh_host_variables(SimpleNamespace(), "host"), ({}, None))

	def test_ansible_execution_inputs_are_redacted_only_in_persisted_copy(self):
		variables = {
			"agent_password": "agent-secret",
			"certificate_private_key": "tls-private-key",
			"nested": {"api_token": "press-token", "ordinary": "visible"},
			"ssh_keys": ["private-ssh-material"],
		}
		persisted = redact_ansible_secrets(variables)
		self.assertEqual(persisted["agent_password"], "[REDACTED]")
		self.assertEqual(persisted["certificate_private_key"], "[REDACTED]")
		self.assertEqual(persisted["nested"]["api_token"], "[REDACTED]")
		self.assertEqual(persisted["nested"]["ordinary"], "visible")
		self.assertEqual(persisted["ssh_keys"], "[REDACTED]")
		self.assertEqual(variables["agent_password"], "agent-secret")
