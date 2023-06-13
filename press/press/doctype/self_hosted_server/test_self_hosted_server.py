# Copyright (c) 2023, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

from press.press.doctype.self_hosted_server.self_hosted_server import SelfHostedServer
import frappe
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
			new=lambda x: create_test_ansible_play(server.name, {"server": "ssl.fc.dev"}),
		):
			server.setup_nginx()
		post_setup_count = frappe.db.count("TLS Certificate")
		self.assertEqual(pre_setup_count, post_setup_count - 1)


def create_test_self_hosted_server(host) -> SelfHostedServer:
	return frappe.get_doc(
		{
			"doctype": "Self Hosted Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"server_url": f"https://{host}.fc.dev",
			"team": create_test_team().name,
		}
	).insert(ignore_if_duplicate=True)


def create_test_ansible_play(server: str, vars: dict = {}):
	play = frappe.get_doc(
		{
			"doctype": "Ansible Play",
			"status": "Success",
			"play": "Setup Self Hosted Nginx",
			"playbook": "self_hosted_nginx.yml",
			"server_type": "Self Hosted Server",
			"server": server,
			"variable": vars,
		}
	).insert()
	play.db_set("status", "Success")
	play.reload()
	return play
