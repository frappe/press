from types import SimpleNamespace
from unittest import TestCase

from press.runner import get_server_ssh_host_variables


class TestBuildOnlySSHHostKeyChecking(TestCase):
	def test_build_only_hosts_require_the_press_known_hosts_file(self):
		settings = get_server_ssh_host_variables(SimpleNamespace(is_build_only=True))

		self.assertIs(settings["ansible_ssh_host_key_checking"], True)
		self.assertEqual(
			settings["ansible_ssh_common_args"],
			"-o UserKnownHostsFile=/home/frappe/.ssh/known_hosts",
		)

	def test_existing_servers_keep_their_current_ssh_behavior(self):
		self.assertEqual(get_server_ssh_host_variables(SimpleNamespace(is_build_only=False)), {})
		self.assertEqual(get_server_ssh_host_variables(SimpleNamespace()), {})
