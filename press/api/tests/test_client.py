# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access import ownership
from press.api.client import (
	ALLOWED_DOCTYPES,
	check_document_access,
	check_document_write_access,
	get,
	get_list,
	set_value,
)
from press.overrides import before_request
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team


def sign_in_as(team):
	"""Put the request-scoped team in place the way `before_request` does."""
	frappe.set_user(team.user)
	before_request()


class TestOwnershipPolicy(FrappeTestCase):
	"""Every doctype the dashboard can reach has to say who owns it."""

	def test_every_allowed_doctype_says_who_owns_it(self):
		undeclared = []
		for doctype in set(ALLOWED_DOCTYPES):
			meta = frappe.get_meta(doctype)
			if meta.istable or meta.has_field("team"):
				continue
			if (
				doctype in ownership.GLOBAL_DOCTYPES
				or doctype in ownership.TEAM_FIELDS
				or doctype in ownership.USER_FIELDS
				or doctype in ownership.LINKED_OWNERS
				or doctype in ownership.DYNAMICALLY_LINKED_OWNERS
			):
				continue
			undeclared.append(doctype)

		self.assertEqual(
			undeclared,
			[],
			f"Add {undeclared} to press.access.ownership or drop them from ALLOWED_DOCTYPES",
		)

	def test_declared_owner_fields_exist(self):
		for doctype, fieldnames in ownership.TEAM_FIELDS.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fieldnames:
				self.assertTrue(
					fieldname == "name" or meta.has_field(fieldname),
					f"{doctype} has no field {fieldname}",
				)

		for doctype, fieldname in ownership.USER_FIELDS.items():
			self.assertTrue(frappe.get_meta(doctype).has_field(fieldname))

	def test_linked_owners_point_at_doctypes_that_carry_a_team(self):
		for doctype, (link_field, linked_doctype) in ownership.LINKED_OWNERS.items():
			self.assertTrue(frappe.get_meta(doctype).has_field(link_field))
			self.assertTrue(
				frappe.get_meta(linked_doctype).has_field("team"),
				f"{linked_doctype} has no team field, so {doctype} cannot be scoped through it",
			)

	def test_global_doctypes_are_reference_data_only(self):
		"""Nothing a team owns may be declared global."""
		for doctype in ownership.GLOBAL_DOCTYPES:
			self.assertFalse(
				frappe.get_meta(doctype).has_field("team"),
				f"{doctype} has a team field, so it is not global reference data",
			)


# Support Access mails the target team on insert and on every status change.
@patch("frappe.sendmail", new=Mock())
class TestDocumentAccess(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.other_team = create_test_press_admin_team()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_support_access(self, requested_team, target_team):
		"""`target_team` is derived from the resources the request asks for."""
		site = create_test_site(team=target_team.name)
		return frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": requested_team.user,
				"requested_team": requested_team.name,
				"reason": "Debugging",
				"status": "Pending",
				"resources": [{"document_type": "Site", "document_name": site.name}],
			}
		).insert(ignore_permissions=True)

	def test_get_list_hides_support_access_of_other_teams(self):
		mine = self.create_support_access(self.team, self.other_team)
		self.create_support_access(self.other_team, self.other_team)

		sign_in_as(self.team)
		names = [row.name for row in get_list("Support Access", limit=100)]

		self.assertEqual(names, [mine.name])

	def test_get_denies_support_access_of_another_team(self):
		theirs = self.create_support_access(self.other_team, self.other_team)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			get("Support Access", theirs.name)

	def test_check_document_access_denies_a_document_with_no_owning_team(self):
		theirs = self.create_support_access(self.other_team, self.other_team)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			check_document_access("Support Access", theirs.name)

	def test_check_document_access_allows_the_owning_team(self):
		mine = self.create_support_access(self.team, self.other_team)

		sign_in_as(self.team)
		check_document_access("Support Access", mine.name)

	def test_reference_data_is_readable_but_not_writable(self):
		plan = frappe.get_all("Site Plan", limit=1, pluck="name")
		if not plan:
			self.skipTest("no Site Plan on this site")

		sign_in_as(self.team)
		check_document_access("Site Plan", plan[0])
		with self.assertRaises(frappe.PermissionError):
			check_document_write_access("Site Plan", plan[0])

	def test_set_value_cannot_change_reference_data(self):
		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Press Settings", "Press Settings", {"partnership_fee_inr": 1})

	def test_ssh_key_belongs_to_the_user_that_added_it(self):
		key = frappe.get_doc(
			{
				"doctype": "User SSH Key",
				"user": self.other_team.user,
				"ssh_public_key": "ssh-ed25519 AAAA test",
				"is_removed": 1,
			}
		).insert(ignore_permissions=True)

		sign_in_as(self.team)
		self.assertFalse(ownership.has_document_access("User SSH Key", key.name))

		sign_in_as(self.other_team)
		self.assertTrue(ownership.has_document_access("User SSH Key", key.name))

	def test_child_row_is_owned_by_whoever_owns_its_parent(self):
		site = create_test_site(team=self.other_team.name)
		site.append("configuration", {"key": "test_key", "value": "test_value", "type": "String"})
		site.save(ignore_permissions=True)
		row = site.configuration[-1]

		sign_in_as(self.team)
		self.assertFalse(ownership.has_document_access("Site Config", row.name))

		sign_in_as(self.other_team)
		self.assertTrue(ownership.has_document_access("Site Config", row.name))

	def test_child_rows_are_bound_to_the_parent_doctype_the_caller_named(self):
		"""A caller naming a parent doctype it owns must not reach other children.

		The team check runs against whichever parent table `parenttype` picks, so
		the query also has to require that the rows really hang off that doctype.
		"""
		site = create_test_site(team=self.team.name)
		site.append("configuration", {"key": "test_key", "value": "test_value", "type": "String"})
		site.save(ignore_permissions=True)

		sign_in_as(self.team)
		mine = get_list(
			"Site Config",
			fields=["name", "key"],
			filters={"parenttype": "Site", "parent": site.name},
		)
		self.assertIn("test_key", [row.key for row in mine])

		lying = get_list(
			"Lead Followup",
			fields=["name"],
			filters={"parenttype": "Site", "parent": site.name},
		)
		self.assertEqual(lying, [])
