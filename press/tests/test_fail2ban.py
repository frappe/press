from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.bastion_server.test_bastion_server import create_test_bastion_server
from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.security import fail2ban
from press.utils.test import foreground_enqueue_doc


def create_test_proxy_server_with_ip():
	proxy = create_test_proxy_server()
	proxy.db_set("ip", frappe.mock("ipv4"))
	return proxy


class TestFail2BanIgnoreList(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_ignore_list_has_private_networks_proxies_bastions_and_press_settings_ips(self):
		proxy = create_test_proxy_server_with_ip()
		bastion = create_test_bastion_server()
		settings = create_test_press_settings()
		settings.fail2ban_ignore_ips = "203.0.113.7\n198.51.100.0/24"
		settings.save()

		ignored = fail2ban.ignore_ips().split()

		for ip in (
			"10.0.0.0/8",
			"172.16.0.0/12",
			"192.168.0.0/16",
			proxy.ip,
			bastion.ip,
			"203.0.113.7",
			"198.51.100.0/24",
		):
			self.assertIn(ip, ignored)

	def test_ignore_list_leaves_out_archived_proxies_and_bastions(self):
		proxy = create_test_proxy_server_with_ip()
		proxy.db_set("status", "Archived")
		bastion = create_test_bastion_server(status="Archived")

		ignored = fail2ban.ignore_ips().split()

		self.assertNotIn(proxy.ip, ignored)
		self.assertNotIn(bastion.ip, ignored)

	def test_press_settings_rejects_ignore_ip_that_is_not_an_address_or_network(self):
		settings = create_test_press_settings()
		settings.fail2ban_ignore_ips = "203.0.113.7\npress.frappe.cloud"

		with self.assertRaises(frappe.ValidationError) as context:
			settings.save()

		self.assertIn(
			"press.frappe.cloud in Fail2Ban Ignore IPs is not an IP address", str(context.exception)
		)

	@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
	@patch("press.press.doctype.server.server.Ansible")
	def test_setup_fail2ban_runs_fail2ban_play_with_the_ignore_list(self, ansible: Mock):
		proxy = create_test_proxy_server()

		proxy.setup_fail2ban()

		ansible.assert_called_once()
		self.assertEqual(ansible.call_args.kwargs["playbook"], "fail2ban.yml")
		self.assertEqual(
			ansible.call_args.kwargs["variables"], {"fail2ban_ignore_ips": fail2ban.ignore_ips()}
		)
		ansible.return_value.run.assert_called_once()
