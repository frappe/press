# Copyright (c) 2023, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch
from press.press.doctype.ansible_play.test_ansible_play import create_test_ansible_play

from press.press.doctype.self_hosted_server.self_hosted_server import SelfHostedServer
import frappe
import json
from press.runner import Ansible
from press.press.doctype.team.test_team import create_test_team
from frappe.tests.utils import FrappeTestCase


class TestSelfHostedServer(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_autoname_to_fqdn(self):
		hostnames = ["a1", "a1.b1", "waaaaaaawwwaawwa", "1234561234"]
		for host in hostnames:
			server = create_test_self_hosted_server(host)
			self.assertEqual(server.name, f"{host}.fc.dev")

	@patch(
		"press.press.doctype.self_hosted_server.self_hosted_server.Ansible",
		wraps=Ansible,
	)
	@patch.object(Ansible, "run", new=Mock())
	def test_setup_nginx_triggers_nginx_ssl_playbook(self, Mock_Ansible: Mock):
		server = create_test_self_hosted_server("ssl")
		server.setup_nginx()
		Mock_Ansible.assert_called_with(
			playbook="self_hosted_nginx.yml",
			server=server,
			user=server.ssh_user or "root",
			port=server.ssh_port or "22",
			variables={"domain": server.name},
		)

	def test_setup_nginx_creates_tls_certificate_post_success(self):
		server = create_test_self_hosted_server("ssl")
		pre_setup_count = frappe.db.count("TLS Certificate")
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: create_test_ansible_play(
				"Setup Self Hosted Nginx",
				"self_hosted_nginx.yml",
				server.doctype,
				server.name,
				{"server": "ssl.fc.dev"},
			),
		):
			server.create_tls_certs()
		post_setup_count = frappe.db.count("TLS Certificate")
		self.assertEqual(pre_setup_count, post_setup_count - 1)

	def test_successful_ping_ansible_sets_status_to_pending(self):
		server = create_test_self_hosted_server("pinger")
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: create_test_ansible_play(
				"Ping Server",
				"ping.yml",
				server.doctype,
				server.name,
				{"server": server.name},
			),
		):
			server.ping_ansible()
		self.assertEqual(server.status, "Pending")

	def test_failed_ping_ansible_sets_status_to_unreachable(self):
		server = create_test_self_hosted_server("pinger")
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: create_test_ansible_play(
				"Ping Server",
				"ping.yml",
				server.doctype,
				server.name,
				{"server": server.name},
				"Failure",
			),
		):
			server.ping_ansible()
		self.assertEqual(server.status, "Unreachable")

	def _create_test_ansible_play_and_task(
		self, server: SelfHostedServer, playbook: str, play: str, task: str, task_output: str
	):  # TODO: Move to AnsiblePlay and Make a generic one for AnsibleTask
		play = create_test_ansible_play(
			play,
			playbook,
			server.doctype,
			server.name,
			{"server": server.name},
		)
		task = frappe.get_doc(
			{
				"doctype": "Ansible Task",
				"status": "Success",
				"play": play.name,
				"role": play.playbook.split(".")[0],
				"task": task,
				"output": task_output,
			}
		)
		task.insert()
		return play

	def test_get_apps_populates_apps_child_table(self):
		server = create_test_self_hosted_server("apps")
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: self._create_test_ansible_play_and_task(
				server,
				"get_apps.yml",
				"Get Bench data from Self Hosted Server",
				"Get Versions from Current Bench",
				json.dumps([{'commit': '3672c9f', 'app': 'frappe', 'branch': 'version-14', 'version': '14.30.0'}]),
			),
		):
			server._get_apps()
		server.reload()
		self.assertTrue(server.apps)
		self.assertEqual(len(server.apps), 1)
		self.assertEqual(server.apps[0].app_name, "frappe")
		self.assertEqual(server.apps[0].branch, "version-14")
		self.assertEqual(server.apps[0].version, "14.30.0")

def create_test_self_hosted_server(host) -> SelfHostedServer:
	server = frappe.get_doc(
		{
			"doctype": "Self Hosted Server",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"server_url": f"https://{host}.fc.dev",
			"team": create_test_team().name,
		}
	).insert(ignore_if_duplicate=True)
	server.reload()
	return server
