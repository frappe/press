# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.client import get, get_list, search_link
from press.api.incident import get_visible_servers
from press.api.notifications import get_notifications, get_unread_count, mark_all_notifications_as_read
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.press_role.test_press_role import create_permission_role, create_user
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_team


class TestRoleRestrictedLists(FrappeTestCase):
	"""A member with a restricted Press Role sees only what the role grants."""

	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		app = create_test_app()
		self.granted_group = create_test_release_group([app], user=self.team.user)
		self.hidden_group = create_test_release_group([app], user=self.team.user)
		self.granted_site = self.create_site(self.granted_group)
		self.hidden_site = self.create_site(self.hidden_group)
		self.member = create_user(f"{frappe.generate_hash(length=8)}@example.com").name
		self.team.append("team_members", {"user": self.member})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.add_user(self.member)
		self.role.add_resource([{"document_type": "Site", "document_name": self.granted_site.name}])

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_site(self, group):
		bench = create_test_bench(group=group)
		return create_test_site(bench=bench.name, team=self.team.name)

	@contextmanager
	def as_user(self, user: str):
		frappe.set_user(user)
		frappe.local.request = frappe._dict(method="POST", headers={"X-Press-Team": self.team.name})
		try:
			yield
		finally:
			del frappe.local.request
			frappe.set_user("Administrator")

	def notify(self, type: str = "Site Update", **fields) -> str:
		notification = frappe.get_doc(
			{"doctype": "Press Notification", "team": self.team.name, "type": type, "message": type, **fields}
		)
		notification.flags.ignore_links = True
		return notification.insert(ignore_permissions=True).name

	def add_member_without_role_to_relaxed_team(self) -> str:
		member = create_user(f"{frappe.generate_hash(length=8)}@example.com").name
		self.team.append("team_members", {"user": member})
		self.team.relaxed_permissions = 1
		self.team.save()
		return member

	def notify_about_database_server(self, database_server: str) -> str:
		return self.notify(
			document_type="Database Server",
			document_name=database_server,
			reference_doctype="Database Server",
			reference_name=database_server,
		)

	def notify_about_site(self, site) -> str:
		return self.notify(
			document_type="Site", document_name=site.name, reference_doctype="Site", reference_name=site.name
		)

	def test_restricted_member_sees_notifications_only_for_sites_their_role_grants(self):
		granted = self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)

		with self.as_user(self.member):
			names = [notification.name for notification in get_notifications()]

		self.assertEqual(names, [granted])

	def test_restricted_member_unread_count_leaves_out_notifications_outside_their_role(self):
		self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)

		with self.as_user(self.member):
			self.assertEqual(get_unread_count(), 1)

	def test_restricted_member_marking_all_read_leaves_notifications_outside_their_role_unread(self):
		granted = self.notify_about_site(self.granted_site)
		hidden = self.notify_about_site(self.hidden_site)

		with self.as_user(self.member):
			mark_all_notifications_as_read()

		self.assertEqual(frappe.db.get_value("Press Notification", granted, "read"), 1)
		self.assertEqual(frappe.db.get_value("Press Notification", hidden, "read"), 0)

	def test_restricted_member_does_not_see_a_notification_without_a_reference(self):
		self.notify(type="Site Migrate", document_type="Site", document_name=self.hidden_site.name)

		with self.as_user(self.member):
			self.assertEqual(get_notifications(), [])
			self.assertEqual(get_unread_count(), 0)

	def test_restricted_member_still_sees_support_access_notifications(self):
		request = self.notify(type="Support Access", document_type="Support Access", document_name="fake")

		with self.as_user(self.member):
			names = [notification.name for notification in get_notifications()]

		self.assertEqual(names, [request])

	def test_member_whose_role_grants_all_sites_sees_notifications_for_every_site(self):
		self.role.db_set("all_sites", 1)
		self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)

		with self.as_user(self.member):
			self.assertEqual(get_unread_count(), 2)

	def test_team_owner_sees_every_notification_of_the_team(self):
		self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)
		self.notify(type="Site Migrate", document_type="Site", document_name=self.hidden_site.name)

		with self.as_user(self.team.user):
			self.assertEqual(get_unread_count(), 3)

	def test_incidents_cover_only_the_servers_of_sites_the_role_grants(self):
		with self.as_user(self.member):
			servers = get_visible_servers(self.team.name)

		self.assertEqual(servers, {self.granted_site.server})

	def test_incidents_cover_no_server_when_the_role_grants_nothing(self):
		self.role.reload()
		self.role.resources = []
		self.role.save()

		with self.as_user(self.member):
			self.assertEqual(get_visible_servers(self.team.name), set())

	def test_team_owner_sees_incidents_of_every_team_site(self):
		with self.as_user(self.team.user):
			servers = get_visible_servers(self.team.name)

		self.assertEqual(servers, {self.granted_site.server, self.hidden_site.server})

	def test_bench_search_lists_only_benches_of_release_groups_the_role_grants(self):
		self.role.add_resource([{"document_type": "Release Group", "document_name": self.granted_group.name}])

		with self.as_user(self.member):
			benches = {row.value for row in search_link("Bench")}

		self.assertEqual(benches, {self.granted_site.bench})

	def test_bench_search_lists_nothing_when_the_role_grants_no_release_group(self):
		with self.as_user(self.member):
			self.assertEqual(search_link("Bench"), [])

	def test_member_without_role_in_relaxed_team_sees_every_notification(self):
		member = self.add_member_without_role_to_relaxed_team()
		self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)
		self.notify(type="Site Migrate", document_type="Site", document_name=self.hidden_site.name)

		with self.as_user(member):
			self.assertEqual(get_unread_count(), 3)

	def test_member_without_role_in_relaxed_team_sees_incidents_of_every_team_site(self):
		member = self.add_member_without_role_to_relaxed_team()

		with self.as_user(member):
			servers = get_visible_servers(self.team.name)

		self.assertEqual(servers, {self.granted_site.server, self.hidden_site.server})

	def test_member_without_role_in_relaxed_team_finds_benches_of_every_release_group(self):
		member = self.add_member_without_role_to_relaxed_team()

		with self.as_user(member):
			benches = {row.value for row in search_link("Bench")}

		self.assertEqual(benches, {self.granted_site.bench, self.hidden_site.bench})

	def test_restricted_member_sees_database_server_notification_when_role_grants_its_app_server(self):
		database_server = create_test_database_server().name
		server = create_test_server(database_server=database_server, team=self.team.name)
		self.role.add_resource([{"document_type": "Server", "document_name": server.name}])
		granted = self.notify_about_database_server(database_server)

		with self.as_user(self.member):
			names = [notification.name for notification in get_notifications()]

		self.assertEqual(names, [granted])

	def test_restricted_member_sees_replica_notification_when_role_grants_the_primary_app_server(self):
		database_server = create_test_database_server().name
		replica = create_test_database_server()
		replica.db_set("primary", database_server)
		server = create_test_server(database_server=database_server, team=self.team.name)
		self.role.add_resource([{"document_type": "Server", "document_name": server.name}])
		granted = self.notify_about_database_server(replica.name)

		with self.as_user(self.member):
			names = [notification.name for notification in get_notifications()]

		self.assertEqual(names, [granted])

	def test_restricted_member_does_not_see_database_server_notification_when_role_hides_its_app_server(
		self,
	):
		database_server = create_test_database_server().name
		create_test_server(database_server=database_server, team=self.team.name)
		self.notify_about_database_server(database_server)

		with self.as_user(self.member):
			self.assertEqual(get_notifications(), [])
			self.assertEqual(get_unread_count(), 0)

	def test_member_whose_role_grants_all_servers_sees_every_database_server_notification(self):
		self.role.db_set("all_servers", 1)
		self.notify_about_database_server(create_test_database_server().name)

		with self.as_user(self.member):
			self.assertEqual(get_unread_count(), 1)

	def test_restricted_member_get_list_returns_only_notifications_their_role_grants(self):
		granted = self.notify_about_site(self.granted_site)
		self.notify_about_site(self.hidden_site)

		with self.as_user(self.member):
			names = [row.name for row in get_list("Press Notification", fields=["name"])]

		self.assertEqual(names, [granted])

	def test_restricted_member_get_list_by_document_finds_notification_of_granted_site(self):
		granted = self.notify_about_site(self.granted_site)
		filters = {"document_type": "Site", "document_name": self.granted_site.name}

		with self.as_user(self.member):
			names = [row.name for row in get_list("Press Notification", fields=["name"], filters=filters)]

		self.assertEqual(names, [granted])

	def test_restricted_member_cannot_get_notification_outside_their_role_by_name(self):
		hidden = self.notify_about_site(self.hidden_site)
		frappe.get_doc("User", self.member).add_roles("Press User")

		with (
			self.as_user(self.member),
			self.assertRaisesRegex(
				frappe.PermissionError, "You do not have permission to access this Press Notification"
			),
		):
			get("Press Notification", hidden)

	def test_restricted_member_can_get_notification_their_role_grants_by_name(self):
		granted = self.notify_about_site(self.granted_site)
		frappe.get_doc("User", self.member).add_roles("Press User")

		with self.as_user(self.member):
			self.assertEqual(get("Press Notification", granted).name, granted)
