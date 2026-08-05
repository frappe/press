# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.api.account import get_user_banners
from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.dashboard_banner.dashboard_banner import (
	DISK_FULL_ALERT,
	DISK_FULL_BANNER,
)
from press.press.doctype.prometheus_alert_rule.test_prometheus_alert_rule import (
	create_test_prometheus_alert_rule,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_site


class TestDashboardBanner(FrappeTestCase):
	def setUp(self):
		self.rule = create_test_prometheus_alert_rule(name=DISK_FULL_ALERT)
		self.server = create_test_server()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def disk_full_alert(self, instance: str, status: str):
		create_test_alertmanager_webhook_log(alert=self.rule, instance=instance, status=status)

	def banner_servers(self) -> list[str]:
		name = frappe.db.get_value("Dashboard Banner", {"title": DISK_FULL_BANNER["title"]})
		if not name:
			return []
		banner = frappe.get_doc("Dashboard Banner", name)
		return [row.server for row in banner.server] if banner.enabled else []

	def test_disk_full_alert_on_app_server_shows_banner_for_that_server(self):
		self.disk_full_alert(self.server.name, "firing")
		self.assertEqual(self.banner_servers(), [self.server.name])

	def test_disk_full_alert_on_database_server_shows_banner_for_its_app_server(self):
		self.disk_full_alert(self.server.database_server, "firing")
		self.assertEqual(self.banner_servers(), [self.server.name])

	def test_resolved_disk_full_alert_hides_the_banner(self):
		self.disk_full_alert(self.server.name, "firing")
		self.disk_full_alert(self.server.name, "resolved")
		self.assertEqual(self.banner_servers(), [])

	def test_resolved_alert_keeps_banner_for_the_servers_still_out_of_space(self):
		other_server = create_test_server()
		self.disk_full_alert(self.server.name, "firing")
		self.disk_full_alert(other_server.name, "firing")

		self.disk_full_alert(self.server.name, "resolved")

		self.assertEqual(self.banner_servers(), [other_server.name])

	def test_unified_server_is_shown_only_once(self):
		frappe.db.set_value(
			"Server", self.server.name, {"database_server": self.server.name, "is_unified_server": 1}
		)

		self.disk_full_alert(self.server.name, "firing")

		self.assertEqual(self.banner_servers(), [self.server.name])

	def test_banner_reaches_a_team_that_only_owns_a_site_on_the_full_server(self):
		site = create_test_site(server=self.server.name)
		self.disk_full_alert(self.server.name, "firing")

		frappe.set_user(frappe.db.get_value("Team", site.team, "user"))
		banner = find(get_user_banners(), lambda b: b["title"] == DISK_FULL_BANNER["title"])

		self.assertIsNotNone(banner)
		self.assertEqual(banner["type_of_scope"], "Server")
		self.assertEqual(banner["server"], [self.server.name])

	def test_alert_on_an_unknown_instance_does_not_show_a_banner(self):
		self.disk_full_alert("some-server-we-do-not-own.frappe.cloud", "firing")
		self.assertEqual(self.banner_servers(), [])
