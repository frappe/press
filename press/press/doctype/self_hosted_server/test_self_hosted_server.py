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
		from press.press.doctype.plan.test_plan import create_test_plan

		create_test_plan(
			"Self Hosted Server", plan_title="Self Hosted Server", plan_name="Self Hosted Server"
		)
		server = create_test_self_hosted_server("ssl", plan="Self Hosted Server")
		app_server = server.create_server()
		server.setup_nginx()
		Mock_Ansible.assert_called_with(
			playbook="self_hosted_nginx.yml",
			server=app_server,
			user=app_server.ssh_user or "root",
			port=app_server.ssh_port or "22",
			variables={
				"domain": server.name,
				"press_domain": frappe.db.get_single_value("Press Settings", "domain"),
			},
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

	def test_get_apps_populates_apps_child_table(self):
		server = create_test_self_hosted_server("apps")
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: _create_test_ansible_play_and_task(
				server=server,
				playbook="get_apps.yml",
				_play="Get Bench data from Self Hosted Server",
				task_1="Get Versions from Current Bench",
				task_1_output=json.dumps(
					[
						{
							"commit": "3672c9f",
							"app": "frappe",
							"branch": "version-14",
							"version": "14.30.0",
						}
					]
				),
				task_1_result="",
			),
		):
			server._get_apps()
		server.reload()
		self.assertTrue(server.apps)
		self.assertEqual(len(server.apps), 1)
		self.assertEqual(server.apps[0].app_name, "frappe")
		self.assertEqual(server.apps[0].branch, "version-14")
		self.assertEqual(server.apps[0].version, "14.30.0")

	def test_get_sites_populates_site_table_with_config(self):
		server = create_test_self_hosted_server("sites")
		server.bench_path = "/home/frappe/frappe-bench"
		with patch(
			"press.press.doctype.self_hosted_server.self_hosted_server.Ansible.run",
			new=lambda x: _create_test_ansible_play_and_task(
				server=server,
				playbook="get_sites.yml",
				_play="Sites from Current Bench",
				task_1="Get Sites from Current Bench",
				task_1_output=json.dumps({"site1.local": ["frappe", "erpnext"]}),
				task_1_result="",
				task_2="Get Site Configs from Existing Sites",
				task_2_output=json.dumps(
					[
						{
							"site": "site1.local",
							"config": {
								"activations_last_sync_date": "2023-05-07 00:00:49.152290",
								"always_use_account_email_id_as_sender": 1,
							},
						}
					]
				),
				task_2_result="",
			),
		):
			server._get_sites()
		server.reload()
		self.assertTrue(server.sites)
		self.assertTrue(server.sites[0].site_config)
		self.assertEqual(len(server.sites), 1)
		self.assertEqual(
			server.sites[0].site_config,
			json.dumps(
				{
					"activations_last_sync_date": "2023-05-07 00:00:49.152290",
					"always_use_account_email_id_as_sender": 1,
				}
			),
		)
		self.assertEqual(server.sites[0].apps, "frappe,erpnext")

	def test_fetch_system_ram_from_ansible_and_update_ram_field(self):
		server = create_test_self_hosted_server("ram")
		_create_test_ansible_play_and_task(
			server=server,
			playbook="ping.yml",
			_play="Ping Server",
			task_1="Gather Facts",
			task_1_output="",
			task_1_result='{"ansible_facts": {"memtotal_mb": 16384}}',
		)
		server.fetch_system_ram()
		server.reload()
		self.assertEqual(server.ram, "16384")

	def test_fetch_system_specifications_and_populate_fields_in_doc(self):
		server = create_test_self_hosted_server("tester")
		_create_test_ansible_play_and_task(
			server=server,
			playbook="ping.yml",
			_play="Ping Server",
			task_1="Gather Facts",
			task_1_output="",
			task_1_result="""{"ansible_facts": {"memtotal_mb": 16384,"system_vendor":"Amazon EC2","processor_vcpus":2,"swaptotal_mb":1024,"architecture":"x86_64","product_name":"c5a.6xLarge","processor":["0","GenuineIntel","Intel(R) Xeon(R) CPU @ 2.20GHz","1","GenuineIntel","Intel(R) Xeon(R) CPU @ 2.20GHz"],"lsb":{"description":"Debian GNU/Linux 11 (bullseye)"},"devices":{"nvme0n1":{"size":"25 GB"}}}}""",
		)
		server.fetch_system_specifications()
		server.reload()
		self.assertEqual(server.vendor, "Amazon EC2")
		self.assertEqual(server.ram, "16384")
		self.assertEqual(server.vcpus, "2")
		self.assertEqual(server.processor, "Intel(R) Xeon(R) CPU @ 2.20GHz")
		self.assertEqual(server.swap_total, "1024")
		self.assertEqual(server.architecture, "x86_64")
		self.assertEqual(server.instance_type, "c5a.6xLarge")
		self.assertEqual(server.distribution, "Debian GNU/Linux 11 (bullseye)")
		self.assertEqual(server.total_storage, "25 GB")

	def test_fetch_private_ip_from_ansible_ping_and_populate_field(self):
		server = create_test_self_hosted_server("tester")
		_create_test_ansible_play_and_task(
			server=server,
			playbook="ping.yml",
			_play="Ping Server",
			task_1="Gather Facts",
			task_1_output="",
			task_1_result="""{"ansible_facts":{"default_ipv4":{"address":"192.168.1.1"},"system_vendor":"AWS EC2"}}""",
		)
		server.fetch_private_ip()
		server.reload()
		self.assertEqual(server.private_ip, "192.168.1.1")

	def test_create_server_and_check_total_records(self):
		from press.press.doctype.cluster.test_cluster import create_test_cluster
		from press.press.doctype.proxy_server.test_proxy_server import (
			create_test_proxy_server,
		)
		from press.press.doctype.plan.test_plan import create_test_plan

		create_test_cluster(name="Default", hybrid=True)
		create_test_proxy_server()
		create_test_plan(
			"Self Hosted Server", plan_title="Self Hosted Server", plan_name="Self Hosted Server"
		)
		pre_server_count = frappe.db.count("Server")

		server = create_test_self_hosted_server("tester", plan="Self Hosted Server")
		server.create_server()
		server.reload()

		post_server_count = frappe.db.count("Server")
		new_server = frappe.get_last_doc("Server")
		self.assertEqual(pre_server_count, post_server_count - 1)
		self.assertEqual("f-default-tester.fc.dev", new_server.name)

	def test_create_db_server_and_check_total_records(self):
		from press.press.doctype.cluster.test_cluster import create_test_cluster
		from press.press.doctype.proxy_server.test_proxy_server import (
			create_test_proxy_server,
		)
		from press.press.doctype.plan.test_plan import create_test_plan

		create_test_plan("Database Server", plan_title="Unlimited", plan_name="Unlimited")
		create_test_cluster(name="Default", hybrid=True)
		create_test_proxy_server()
		pre_server_count = frappe.db.count("Database Server")

		server = create_test_self_hosted_server("tester", database_plan="Unlimited")
		server.create_db_server()
		server.reload()

		post_server_count = frappe.db.count("Database Server")
		new_server = frappe.get_last_doc("Database Server")
		self.assertEqual(pre_server_count, post_server_count - 1)
		self.assertEqual("m-default-tester.fc.dev", new_server.name)

	def test_check_minimum_specs(self):
		server = create_test_self_hosted_server("tester")
		server.ram = 2500
		with self.assertRaises(frappe.exceptions.ValidationError):
			server.check_minimum_specs()
		server.ram = 3853
		server.vcpus = 1
		server.total_storage = "100 GB"
		with self.assertRaises(frappe.exceptions.ValidationError):
			server.check_minimum_specs()
		server.vcpus = 2
		server.total_storage = "20 GB"
		with self.assertRaises(frappe.exceptions.ValidationError):
			server.check_minimum_specs()
		server.total_storage = "100 GB"
		self.assertTrue(server.check_minimum_specs())

	def test_create_subscription_add_plan_change_and_check_for_new_subscription(self):
		from press.press.doctype.plan.test_plan import create_test_plan

		plan = create_test_plan(
			"Self Hosted Server", plan_title="Unlimited", plan_name="Unlimited"
		)
		pre_plan_change_count = frappe.db.count("Plan Change")
		pre_subscription_count = frappe.db.count("Subscription")
		server = create_test_self_hosted_server("tester")
		server.plan = plan.name
		server.create_subscription()
		server.reload()
		post_plan_change_count = frappe.db.count("Plan Change")
		post_subscription_count = frappe.db.count("Subscription")
		self.assertEqual(pre_plan_change_count, post_plan_change_count - 1)
		self.assertEqual(pre_subscription_count, post_subscription_count - 1)


def create_test_self_hosted_server(
	host, database_plan=None, plan=None
) -> SelfHostedServer:
	"""
	Plan: is a string that represents the application servers subscription plan name
	Database Plan: is a string that represents the database servers subscription plan name
	"""
	server = frappe.get_doc(
		{
			"doctype": "Self Hosted Server",
			"ip": frappe.mock("ipv4"),
			"private_ip": "192.168.1.1",
			"mariadb_ip": frappe.mock("ipv4"),
			"mariadb_private_ip": "192.168.1.2",
			"server_url": f"https://{host}.fc.dev",
			"team": create_test_team().name,
			"cluster": "Default",
		}
	)

	if database_plan:
		server.database_plan = database_plan
	if plan:
		server.plan = plan

	server.insert(ignore_if_duplicate=True)
	server.reload()
	return server


def _create_test_ansible_play_and_task(
	server: SelfHostedServer, playbook: str, _play: str, **kwargs
):  # TODO: Move to AnsiblePlay and Make a generic one for AnsibleTask
	play = create_test_ansible_play(
		_play,
		playbook,
		server.doctype,
		server.name,
		{"server": server.name},
	)

	for i, _ in enumerate(kwargs):
		try:
			task = frappe.get_doc(
				{
					"doctype": "Ansible Task",
					"status": "Success",
					"play": play.name,
					"role": play.playbook.split(".")[0],
					"task": kwargs.get("task_" + str(i + 1)),
					"output": kwargs.get("task_" + str(i + 1) + "_output"),
					"result": kwargs.get("task_" + str(i + 1) + "_result"),
				}
			)
			task.insert()
		except Exception:
			pass
	return play
