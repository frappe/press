# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_role.test_press_role import (
	create_permission_role,
	create_test_site_record,
	create_user,
)
from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.team_member_resource.team_member_resource import sync_press_role

if TYPE_CHECKING:
	from press.press.doctype.team_member_resource.team_member_resource import TeamMemberResource


def _add_member(team_doc, email: str) -> str:
	"""Create a user and add them to team_doc's team_members table."""
	create_test_user(email)
	user = frappe.get_value("User", {"email": email}, "name")
	team_doc.append("team_members", {"user": user})
	team_doc.save(ignore_permissions=True)
	team_doc.reload()
	return user


def create_test_team_member_resource(
	team: str,
	user: str,
	document_type: str,
	document_name: str,
) -> TeamMemberResource:
	"""Insert a TeamMemberResource (runs all validation, bypasses Frappe permissions)."""
	return frappe.get_doc(
		{
			"doctype": "Team Member Resource",
			"team": team,
			"user": user,
			"document_type": document_type,
			"document_name": document_name,
		}
	).insert(ignore_permissions=True)


# ══════════════════════════════════════════════════════════════════════════════
# TeamMemberResource validation methods
# ══════════════════════════════════════════════════════════════════════════════


class TestTeamMemberResourceValidation(FrappeTestCase):
	"""Unit-level tests for the validation methods on TeamMemberResource."""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_press_settings()
		self.team = create_test_team()
		self.member_email = frappe.mock("email")
		self.member_user = _add_member(self.team, self.member_email)
		self.server = create_test_server(team=self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ── validate_user ───────────────────────────────────────────────────────

	def test_validate_user_raises_if_user_not_in_team(self):
		"""validate_user() raises ValidationError when the user is not a team member."""
		outsider_email = frappe.mock("email")
		create_test_user(outsider_email)
		outsider = frappe.get_value("User", {"email": outsider_email}, "name")

		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": outsider,
				"document_type": "Server",
				"document_name": self.server.name,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_user()

	def test_validate_user_passes_for_team_member(self):
		"""validate_user() does NOT raise for a legitimate team member."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Server",
				"document_name": self.server.name,
			}
		)
		doc.validate_user()  # must not raise

	# ── validate_document_type ──────────────────────────────────────────────

	def test_validate_document_type_raises_for_invalid_type(self):
		"""validate_document_type() raises for document types outside the permitted set."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Invoice",
				"document_name": "some-invoice",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_document_type()

	def test_validate_document_type_accepts_server(self):
		"""validate_document_type() does NOT raise for 'Server'."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Server",
				"document_name": self.server.name,
			}
		)
		doc.validate_document_type()  # must not raise

	def test_validate_document_type_accepts_release_group(self):
		"""validate_document_type() does NOT raise for 'Release Group'."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Release Group",
				"document_name": "some-group",
			}
		)
		doc.validate_document_type()  # must not raise

	def test_validate_document_type_accepts_site(self):
		"""validate_document_type() does NOT raise for 'Site'."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Site",
				"document_name": "some-site",
			}
		)
		doc.validate_document_type()  # must not raise

	# ── validate_document_name ──────────────────────────────────────────────

	def test_validate_document_name_raises_when_document_belongs_to_different_team(self):
		"""validate_document_name() raises when the document's team differs from the resource team."""
		other_team = create_test_team()
		other_server = create_test_server(team=other_team.name)

		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Server",
				"document_name": other_server.name,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_document_name()

	def test_validate_document_name_passes_when_document_belongs_to_same_team(self):
		"""validate_document_name() does NOT raise when the document belongs to the resource team."""
		doc = frappe.get_doc(
			{
				"doctype": "Team Member Resource",
				"team": self.team.name,
				"user": self.member_user,
				"document_type": "Server",
				"document_name": self.server.name,
			}
		)
		doc.validate_document_name()  # must not raise

	# ── prevent_duplicate ──────────────────────────────────────────────────

	def test_prevent_duplicate_raises_for_identical_resource(self):
		"""before_validate() via prevent_duplicate() raises when a duplicate record exists."""
		create_test_team_member_resource(self.team.name, self.member_user, "Server", self.server.name)

		with self.assertRaises(frappe.ValidationError):
			create_test_team_member_resource(self.team.name, self.member_user, "Server", self.server.name)

	def test_full_insert_creates_resource(self):
		"""A TeamMemberResource with valid data can be inserted successfully."""
		resource = create_test_team_member_resource(
			self.team.name, self.member_user, "Server", self.server.name
		)
		self.assertTrue(frappe.db.exists("Team Member Resource", resource.name))
		self.assertEqual(resource.team, self.team.name)
		self.assertEqual(resource.user, self.member_user)
		self.assertEqual(resource.document_type, "Server")
		self.assertEqual(resource.document_name, self.server.name)


# ══════════════════════════════════════════════════════════════════════════════
# sync_press_role integration tests
# ══════════════════════════════════════════════════════════════════════════════


class TestSyncPressRole(FrappeTestCase):
	"""Integration tests for sync_press_role() using real Press Role and site documents."""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Press Role")
		self.team = create_test_team()
		self.member = create_user(frappe.mock("email"))
		self.team.append("team_members", {"user": self.member.name})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.append("users", {"user": self.member.name})
		self.role.save()
		self.test_sites = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for site_name in self.test_sites:
			frappe.db.sql("DELETE FROM `tabSite` WHERE name = %s", (site_name,))
		frappe.db.delete("Team Member Resource", {"team": self.team.name})
		frappe.delete_doc("Press Role", self.role.name, force=True)
		frappe.delete_doc("Team", self.team.name, force=True)
		frappe.delete_doc("User", self.member.name, force=True)
		frappe.local._current_team = None

	def create_site(self, team_name):
		subdomain = frappe.generate_hash(length=8)
		name = f"{subdomain}.frappe.cloud"
		create_test_site_record(name, subdomain, team_name)
		self.test_sites.append(name)
		return name

	def add_role_resource(self, document_type, document_name):
		resource = self.role.append(
			"resources",
			{
				"document_type": document_type,
				"document_name": document_name,
			},
		)
		resource.db_insert()
		self.role.reload()

	def test_sync_skips_stale_resource(self):
		"""sync_press_role() does not create a resource for a site owned by a different team."""
		other_team = create_test_team()
		self.addCleanup(frappe.delete_doc, "Team", other_team.name, force=True)
		stale_site = self.create_site(other_team.name)
		self.add_role_resource("Site", stale_site)

		sync_press_role(self.role)

		self.assertFalse(
			frappe.db.exists(
				{"doctype": "Team Member Resource", "team": self.team.name, "document_name": stale_site}
			)
		)

	def test_sync_creates_team_member_resource(self):
		"""sync_press_role() creates a TeamMemberResource for a site that belongs to the role's team."""
		valid_site = self.create_site(self.team.name)
		self.add_role_resource("Site", valid_site)

		sync_press_role(self.role)

		self.assertTrue(
			frappe.db.exists(
				{
					"doctype": "Team Member Resource",
					"team": self.team.name,
					"user": self.member.name,
					"document_type": "Site",
					"document_name": valid_site,
				}
			)
		)

	def test_sync_clears_existing_resources_before_rebuild(self):
		"""sync_press_role() deletes all existing resources for the team before recreating."""
		valid_site = self.create_site(self.team.name)
		self.add_role_resource("Site", valid_site)
		sync_press_role(self.role)  # first sync creates the resource

		self.assertTrue(frappe.db.exists("Team Member Resource", {"team": self.team.name}))

		# Remove the resource from the role in the DB so the next sync rebuilds to empty.
		frappe.db.delete("Press Role Resource", {"parent": self.role.name})
		self.role.reload()

		# Second sync: no resources on the role → all TeamMemberResource rows for the
		# team must be deleted and nothing recreated.
		sync_press_role(self.role)

		self.assertFalse(frappe.db.exists("Team Member Resource", {"team": self.team.name}))
