# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_and_update, restart
from press.api.client import check_document_write_access
from press.api.server import reboot
from press.api.site import protected
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.press_role.test_press_role import create_permission_role, create_user
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.team.test_team import create_test_team


class TestRoleGuardOnProtectedEndpoints(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.group = create_test_release_group([create_test_app()], user=self.team.user)
		self.member = create_user(f"{frappe.generate_hash(length=8)}@example.com").name
		self.team.append("team_members", {"user": self.member})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.add_user(self.member)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	@contextmanager
	def as_member(self):
		frappe.set_user(self.member)
		frappe.local.request = frappe._dict(method="POST", headers={"X-Press-Team": self.team.name})
		try:
			yield
		finally:
			del frappe.local.request
			frappe.set_user("Administrator")

	def test_restricted_member_cannot_deploy_a_release_group_their_role_does_not_grant(self):
		with self.as_member(), self.assertRaisesRegex(frappe.PermissionError, "Not Permitted"):
			deploy_and_update(name=self.group.name, apps=[])
		self.assertFalse(frappe.db.exists("Deploy Candidate", {"group": self.group.name}))

	def test_restricted_member_passes_protected_for_a_release_group_their_role_grants(self):
		self.role.add_resource([{"document_type": "Release Group", "document_name": self.group.name}])
		endpoint = protected("Release Group")(lambda name: "allowed")
		with self.as_member():
			self.assertEqual(endpoint(name=self.group.name), "allowed")

	def test_member_passes_protected_when_the_team_has_no_roles(self):
		frappe.delete_doc("Press Role", self.role.name, force=True)
		endpoint = protected("Release Group")(lambda name: "allowed")
		with self.as_member():
			self.assertEqual(endpoint(name=self.group.name), "allowed")

	def test_restricted_member_has_no_write_access_to_a_release_group_their_role_does_not_grant(self):
		with self.as_member(), self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			check_document_write_access("Release Group", self.group.name)

	def test_restricted_member_has_write_access_to_a_release_group_their_role_grants(self):
		self.role.add_resource([{"document_type": "Release Group", "document_name": self.group.name}])
		with self.as_member():
			check_document_write_access("Release Group", self.group.name)

	def create_bench(self) -> str:
		bench = create_test_bench(group=self.group)
		frappe.db.set_value("Bench", bench.name, "team", self.team.name)
		return bench.name

	def create_database_server(self) -> tuple[str, str]:
		database_server = create_test_database_server()
		frappe.db.set_value("Database Server", database_server.name, "team", self.team.name)
		server = create_test_server(database_server=database_server.name, team=self.team.name)
		return server.name, database_server.name

	def test_restricted_member_cannot_restart_a_bench_of_a_release_group_their_role_does_not_grant(self):
		bench = self.create_bench()
		with self.as_member(), self.assertRaisesRegex(frappe.PermissionError, "Not Permitted"):
			restart(name=bench)

	def test_restricted_member_passes_protected_for_a_bench_of_a_release_group_their_role_grants(self):
		bench = self.create_bench()
		self.role.add_resource([{"document_type": "Release Group", "document_name": self.group.name}])
		endpoint = protected("Bench")(lambda name: "allowed")
		with self.as_member():
			self.assertEqual(endpoint(name=bench), "allowed")

	def test_restricted_member_cannot_reboot_a_database_server_of_a_server_their_role_does_not_grant(self):
		_, database_server = self.create_database_server()
		with self.as_member(), self.assertRaisesRegex(frappe.PermissionError, "Not Permitted"):
			reboot(name=database_server)

	def test_restricted_member_passes_protected_for_a_database_server_of_a_server_their_role_grants(self):
		server, database_server = self.create_database_server()
		self.role.add_resource([{"document_type": "Server", "document_name": server}])
		endpoint = protected(["Server", "Database Server"])(lambda name: "allowed")
		with self.as_member():
			self.assertEqual(endpoint(name=database_server), "allowed")
