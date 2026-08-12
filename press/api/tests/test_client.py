# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.model.base_document import get_controller
from frappe.tests.utils import FrappeTestCase

from press.access import ownership
from press.api.client import (
	ALLOWED_DOCTYPES,
	check_document_access,
	check_document_write_access,
	fields_being_set,
	get,
	get_list,
	set_value,
)
from press.overrides import before_request
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.ansible_play.test_ansible_play import create_test_ansible_play
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.subscription.test_subscription import create_test_subscription
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


@patch("frappe.sendmail", new=Mock())
class TestJobAndPlayAccess(FrappeTestCase):
	"""Jobs and plays name no team of their own, and used to be readable by anyone.

	A pen test read another team's Agent Job and Ansible Play straight off
	`press.api.client.get`, which handed back the `owner` of each — the email
	address of whoever on that team ran it.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.other_team = create_test_press_admin_team()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_job_on_bench_of(self, team):
		bench = create_test_bench()
		frappe.db.set_value("Bench", bench.name, "team", team.name)
		job = create_test_agent_job(server=bench.server)
		job.db_set("bench", bench.name)
		return bench, job

	def test_agent_job_belongs_to_whoever_owns_its_bench(self):
		_, job = self.create_job_on_bench_of(self.other_team)

		sign_in_as(self.team)
		self.assertFalse(ownership.has_document_access("Agent Job", job.name))

		sign_in_as(self.other_team)
		self.assertTrue(ownership.has_document_access("Agent Job", job.name))

	def test_get_denies_an_agent_job_belonging_to_another_team(self):
		_, job = self.create_job_on_bench_of(self.other_team)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			get("Agent Job", job.name)

	def test_ansible_play_belongs_to_whoever_owns_the_server_it_ran_on(self):
		server = create_test_server(team=self.other_team.name)
		play = create_test_ansible_play("Set mysqld variable", "mysqld.yml", "Server", server.name)

		sign_in_as(self.team)
		self.assertFalse(ownership.has_document_access("Ansible Play", play.name))

		sign_in_as(self.other_team)
		self.assertTrue(ownership.has_document_access("Ansible Play", play.name))

	def test_get_denies_an_ansible_play_on_another_teams_server(self):
		server = create_test_server(team=self.other_team.name)
		play = create_test_ansible_play("Set mysqld variable", "mysqld.yml", "Server", server.name)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			get("Ansible Play", play.name)

	def test_get_list_denies_agent_jobs_filtered_by_another_teams_bench(self):
		"""`bench` alone satisfied the "name something" check but had no owner check."""
		bench, _ = self.create_job_on_bench_of(self.other_team)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			get_list("Agent Job", fields=["name"], filters={"bench": bench.name})

	def test_get_list_refuses_agent_jobs_when_the_caller_names_nothing(self):
		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			get_list("Agent Job", fields=["name"])


class TestEditableFields(FrappeTestCase):
	"""`dashboard_fields` says what may be read. It must not decide what may be written."""

	def test_editable_fields_are_readable_and_real(self):
		for doctype in set(ALLOWED_DOCTYPES):
			controller = get_controller(doctype)
			editable = getattr(controller, "dashboard_editable_fields", ())
			if not editable:
				continue

			meta = frappe.get_meta(doctype)
			readable = getattr(controller, "dashboard_fields", ())
			for field in editable:
				self.assertTrue(meta.has_field(field), f"{doctype} has no field {field}")
				self.assertIn(
					field,
					readable,
					f"{doctype}.{field} is editable but not in dashboard_fields, so it cannot be read back",
				)

	def test_fields_a_doctype_never_offers_up_stay_unwritable(self):
		"""The fields the reported issue named, plus the ones that would give a site away."""
		site_fields = get_controller("Site").dashboard_editable_fields
		for field in ("plan", "team", "bench", "server", "status", "group"):
			self.assertNotIn(field, site_fields)

		self.assertEqual(getattr(get_controller("Subscription"), "dashboard_editable_fields", ()), ())

	def test_fields_being_set_reads_every_calling_convention(self):
		self.assertEqual(fields_being_set({"plan": "x", "team": "y"}, None), ["plan", "team"])
		self.assertEqual(fields_being_set("plan", "x"), ["plan"])
		self.assertEqual(fields_being_set('{"plan": "x"}', None), ["plan"])
		# A bare fieldname is not JSON, and frappe treats it as one field set to ""
		self.assertEqual(fields_being_set("plan", None), ["plan"])


@patch("frappe.sendmail", new=Mock())
class TestSetValue(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_set_value_refuses_to_change_a_site_plan(self):
		site = create_test_site(team=self.team.name)
		plan = frappe.get_all("Site Plan", limit=1, pluck="name")
		if not plan:
			self.skipTest("no Site Plan on this site")

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Site", site.name, {"plan": plan[0]})

		self.assertNotEqual(frappe.db.get_value("Site", site.name, "plan"), plan[0])

	def test_set_value_refuses_to_hand_a_site_to_another_team(self):
		site = create_test_site(team=self.team.name)
		other_team = create_test_press_admin_team()

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Site", site.name, "team", other_team.name)

		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), self.team.name)

	def test_set_value_allows_a_field_the_doctype_offers_up(self):
		site = create_test_site(team=self.team.name)

		sign_in_as(self.team)
		set_value("Site", site.name, {"skip_auto_updates": 1})

		self.assertEqual(frappe.db.get_value("Site", site.name, "skip_auto_updates"), 1)

	def test_set_value_refuses_a_doctype_that_offers_up_nothing(self):
		site = create_test_site(team=self.team.name)
		plan = create_test_plan("Site")
		subscription = create_test_subscription(site.name, plan.name, self.team.name)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Subscription", subscription.name, {"enabled": 0})

		self.assertEqual(frappe.db.get_value("Subscription", subscription.name, "enabled"), 1)
