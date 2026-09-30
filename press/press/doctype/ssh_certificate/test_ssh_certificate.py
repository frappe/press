# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.ssh_certificate.ssh_certificate import SSHCertificate
from press.press.doctype.team.test_team import create_paid_invoice, create_test_press_admin_team
from press.press.doctype.user_ssh_key.test_user_ssh_key import create_test_user_ssh_key


@patch.object(SSHCertificate, "validate_certificate_authority", new=Mock())
@patch.object(SSHCertificate, "generate_certificate", new=Mock())
@patch.object(SSHCertificate, "extract_certificate_details", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSSHCertificate(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_press_admin_team()
		self.user = self.team.user

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_press_admin_user_can_create_ssh_certificate(self):
		bench = create_test_bench(self.user)
		group = bench.group
		frappe.set_user(self.user)
		user_ssh_key = create_test_user_ssh_key(user=self.user)
		return frappe.get_doc(
			{
				"doctype": "SSH Certificate",
				"certificate_type": "User",
				"group": group,
				"user": frappe.session.user,
				"user_ssh_key": user_ssh_key.name,
				"validity": "6h",
			}
		).insert()

	def create_bench_on_public_server(self):
		server = create_test_server(public=True, team=self.team.name)
		group = create_test_release_group([create_test_app()], self.user, servers=[server.name])
		return create_test_bench(self.user, group=group, server=server.name)

	def sign_in_with_default_ssh_key(self):
		frappe.set_user(self.user)
		create_test_user_ssh_key(user=self.user).db_set("is_default", 1)

	def test_new_team_cannot_generate_certificate_for_group_on_public_server(self):
		bench = self.create_bench_on_public_server()
		self.sign_in_with_default_ssh_key()
		with self.assertRaisesRegex(frappe.ValidationError, "on or after"):
			frappe.get_doc("Release Group", bench.group).generate_certificate()

	def test_new_team_that_bought_credits_can_generate_certificate_and_gets_ssh_access_enabled(self):
		create_paid_invoice(self.team)
		bench = self.create_bench_on_public_server()
		self.sign_in_with_default_ssh_key()
		frappe.get_doc("Release Group", bench.group).generate_certificate()
		self.assertTrue(frappe.db.exists("SSH Certificate", {"group": bench.group, "user": self.user}))
		self.assertTrue(frappe.db.get_value("Team", self.team.name, "ssh_access_enabled"))

	def test_team_with_ssh_access_enabled_can_generate_certificate_on_public_server(self):
		frappe.db.set_value("Team", self.team.name, "ssh_access_enabled", 1)
		bench = self.create_bench_on_public_server()
		self.sign_in_with_default_ssh_key()
		frappe.get_doc("Release Group", bench.group).generate_certificate()
		self.assertTrue(frappe.db.exists("SSH Certificate", {"group": bench.group, "user": self.user}))

	def test_old_team_without_ssh_access_sees_not_enabled_message(self):
		self.team.db_set("creation", add_to_date(None, days=-8))
		bench = self.create_bench_on_public_server()
		self.sign_in_with_default_ssh_key()
		with self.assertRaisesRegex(frappe.ValidationError, "not enabled for your team"):
			frappe.get_doc("Release Group", bench.group).generate_certificate()

	def test_bench_get_doc_reports_unlock_date_for_new_team(self):
		bench = self.create_bench_on_public_server()
		frappe.set_user(self.user)
		doc = frappe._dict()
		bench.get_doc(doc)
		self.assertIn("on or after", doc.ssh_access_denied_reason)
