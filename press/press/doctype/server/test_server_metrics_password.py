# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.server.test_server import create_test_server


class TestServerMetricsPassword(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _reset_given_play_status(self, server, status="Success"):
		with patch("press.press.doctype.server.server.Ansible") as Ansible:
			Ansible.return_value.run.return_value = Mock(status=status)
			password = server.reset_metrics_password()
		return password, Ansible.call_args.kwargs

	def test_reset_metrics_password_sets_the_returned_password_for_the_customer_user(self):
		for server in (create_test_server(), create_test_database_server()):
			with self.subTest(server_type=server.doctype):
				password, ansible_kwargs = self._reset_given_play_status(server)
				self.assertEqual(ansible_kwargs["playbook"], "monitoring_password.yml")
				self.assertEqual(
					ansible_kwargs["variables"],
					{"monitoring_username": "customer", "monitoring_password": password},
				)

	def test_reset_metrics_password_refused_on_public_server_without_running_playbook(self):
		server = create_test_server(public=True)
		with (
			patch("press.press.doctype.server.server.Ansible") as Ansible,
			self.assertRaisesRegex(frappe.ValidationError, "only available on dedicated servers"),
		):
			server.reset_metrics_password()
		Ansible.assert_not_called()

	def test_reset_metrics_password_raises_instead_of_returning_password_when_play_fails(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Could not set the metrics password"):
			self._reset_given_play_status(create_test_server(), status="Failure")
