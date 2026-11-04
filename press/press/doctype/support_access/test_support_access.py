# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from press.access.support_access import has_support_access
from press.api.client import get_list
from press.api.tests.test_client import sign_in_as
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
	create_test_deploy_candidate_build,
)
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.support_access.support_access import SupportAccess, expire_pending_requests
from press.press.doctype.team.test_team import create_test_press_admin_team

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestSupportAccess(UnitTestCase):
	"""
	Unit tests for SupportAccess.
	Use this class for testing individual functions and methods.
	"""

	def test_valid_status_transition(self):
		combinations = [
			["Pending", "Accepted", True],
			["Pending", "Rejected", True],
			["Accepted", "Revoked", True],
			["Accepted", "Forfeited", True],
			["Rejected", "Accepted", False],
			["Forfeited", "Accepted", False],
			["Revoked", "Accepted", False],
			["Pending", "Forfeited", False],
			["Pending", "Revoked", False],
			["Accepted", "Rejected", False],
			["Rejected", "Forfeited", False],
			["Rejected", "Revoked", False],
			["Forfeited", "Revoked", False],
			["Revoked", "Forfeited", False],
			["Pending", "Expired", True],
			["Accepted", "Expired", False],
			["Expired", "Accepted", False],
			["Expired", "Pending", False],
		]

		support_access: SupportAccess = frappe.new_doc("Support Access")
		for status_from, status_to, expected in combinations:
			with self.subTest(status_from=status_from, status_to=status_to, expected=expected):
				is_valid = support_access.is_valid_status_transition(status_from, status_to)
				self.assertEqual(is_valid, expected)


# Support Access mails the target team on insert.
@patch("frappe.sendmail", new=Mock())
class IntegrationTestSupportAccess(IntegrationTestCase):
	"""
	Integration tests for SupportAccess.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.site = create_test_site(team=create_test_press_admin_team().name)

	def tearDown(self):
		frappe.db.rollback()

	def create_support_access(self, status: str = "Pending", days_old: int = 0) -> SupportAccess:
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.team.user,
				"requested_team": self.team.name,
				"reason": "Debugging",
				"status": status,
				"resources": [{"document_type": "Site", "document_name": self.site.name}],
			}
		).insert(ignore_permissions=True)
		creation = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-days_old)
		frappe.db.set_value("Support Access", access.name, "creation", creation, update_modified=False)
		return access

	def status_of(self, access: SupportAccess) -> str:
		return frappe.db.get_value("Support Access", access.name, "status")

	def test_pending_request_older_than_seven_days_is_expired(self):
		access = self.create_support_access(days_old=8)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Expired")

	def test_expired_request_notifies_the_requesting_team(self):
		access = self.create_support_access(days_old=8)
		expire_pending_requests()
		self.assertTrue(
			frappe.db.exists(
				"Press Notification",
				{
					"document_name": access.name,
					"team": self.team.name,
					"title": "Access Request Expired",
				},
			)
		)

	def test_pending_request_younger_than_seven_days_stays_pending(self):
		access = self.create_support_access(days_old=6)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Pending")

	def test_old_request_that_is_not_pending_keeps_its_status(self):
		access = self.create_support_access(status="Rejected", days_old=8)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Rejected")


@patch("frappe.sendmail", new=Mock())
class IntegrationTestSupportAccessToBenchGroup(IntegrationTestCase):
	"""A grant on a bench group covers the deploys, builds and jobs under it."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.group = ReleaseGroup("Release Group", self.site.group)
		self.agent_team = create_test_press_admin_team()
		frappe.get_doc("User", self.agent_team.user).add_roles("Press Support Agent")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def grant(self, document_type: str, document_name: str):
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.agent_team.user,
				"requested_team": self.agent_team.name,
				"reason": "Debugging a failed deploy",
				"resources": [{"document_type": document_type, "document_name": document_name}],
			}
		).insert(ignore_permissions=True)
		allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=1)
		frappe.db.set_value(
			"Support Access", access.name, {"status": "Accepted", "access_allowed_till": allowed_till}
		)

	def create_release_pipeline(self):
		return frappe.get_doc(
			{"doctype": "Release Pipeline", "release_group": self.group.name, "team": self.group.team}
		).insert(ignore_permissions=True)

	def create_build(self):
		candidate = create_test_deploy_candidate(self.group)
		build = create_test_deploy_candidate_build(candidate, no_build=True)
		with patch.object(DeployCandidateBuild, "after_insert", Mock()):
			return build.insert(ignore_permissions=True)

	def create_job(self, site: str | None = None):
		job = create_test_agent_job()
		frappe.db.set_value("Agent Job", job.name, {"bench": self.site.bench, "site": site})
		return job

	def agent_can_read(self, doctype: str, name: str) -> bool:
		frappe.set_user(self.agent_team.user)
		return has_support_access(doctype, name)

	def test_group_grant_lets_support_agent_read_the_release_pipeline(self):
		pipeline = self.create_release_pipeline()
		self.grant("Release Group", self.group.name)
		self.assertTrue(self.agent_can_read("Release Pipeline", pipeline.name))

	def test_support_agent_without_a_grant_cannot_read_the_release_pipeline(self):
		pipeline = self.create_release_pipeline()
		self.assertFalse(self.agent_can_read("Release Pipeline", pipeline.name))

	def test_group_grant_lets_support_agent_read_the_deploy_candidate_build(self):
		build = self.create_build()
		self.grant("Release Group", self.group.name)
		self.assertTrue(self.agent_can_read("Deploy Candidate Build", build.name))
		self.assertTrue(self.agent_can_read("Deploy Candidate", build.deploy_candidate))

	def test_support_agent_without_a_grant_cannot_read_the_deploy_candidate_build(self):
		build = self.create_build()
		self.assertFalse(self.agent_can_read("Deploy Candidate Build", build.name))

	def test_group_grant_lets_support_agent_read_a_bench_job(self):
		job = self.create_job()
		self.grant("Release Group", self.group.name)
		self.assertTrue(self.agent_can_read("Agent Job", job.name))

	def test_site_grant_lets_support_agent_read_the_site_job_but_not_a_bench_job(self):
		site_job = self.create_job(site=self.site.name)
		bench_job = self.create_job()
		self.grant("Site", self.site.name)
		self.assertTrue(self.agent_can_read("Agent Job", site_job.name))
		self.assertFalse(self.agent_can_read("Agent Job", bench_job.name))

	def test_group_grant_lets_support_agent_read_a_site_job_on_the_group_bench(self):
		job = self.create_job(site=self.site.name)
		self.grant("Release Group", self.group.name)
		self.assertTrue(self.agent_can_read("Agent Job", job.name))

	def test_support_agent_without_a_grant_cannot_read_a_site_job(self):
		job = self.create_job(site=self.site.name)
		self.assertFalse(self.agent_can_read("Agent Job", job.name))

	def dependencies_seen_by(self, team, start: int = 0, limit: int = 20) -> list:
		sign_in_as(team)
		filters = {"parenttype": "Release Group", "parent": self.group.name}
		return get_list(
			"Release Group Dependency", fields=["name"], filters=filters, start=start, limit=limit
		)

	def test_group_grant_lets_support_agent_list_the_group_dependencies(self):
		owner_team = frappe.get_doc("Team", self.group.team)
		expected = self.dependencies_seen_by(owner_team)
		self.assertTrue(expected)
		self.grant("Release Group", self.group.name)
		self.assertEqual(self.dependencies_seen_by(self.agent_team), expected)

	def test_support_agent_without_a_grant_cannot_list_the_group_dependencies(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			self.dependencies_seen_by(self.agent_team)

	def test_dependency_list_returns_the_requested_page_not_every_dependency(self):
		owner_team = frappe.get_doc("Team", self.group.team)
		every_dependency = self.dependencies_seen_by(owner_team)
		self.assertGreater(len(every_dependency), 2)
		first_page = self.dependencies_seen_by(owner_team, start=0, limit=2)
		second_page = self.dependencies_seen_by(owner_team, start=2, limit=2)
		self.assertEqual(first_page + second_page, every_dependency[:4])


class IntegrationTestSupportAccessAnswer(IntegrationTestCase):
	"""Only a member of the target team or a System Manager switched into it can answer a request."""

	def setUp(self):
		from press.access.test_employee_consent import create_test_employee

		super().setUp()
		sendmail = patch("frappe.sendmail", new=Mock())
		sendmail.start()
		self.addCleanup(sendmail.stop)
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.employee = create_test_employee()
		self.access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.employee.user,
				"requested_team": self.employee.name,
				"reason": "Debugging",
				"login_as_administrator": 1,
				"resources": [{"document_type": "Site", "document_name": self.site.name}],
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def act_in_site_team_as(self, user: str) -> SupportAccess:
		frappe.set_user(user)
		switched = patch(
			"press.press.doctype.support_access.support_access.get_current_team",
			return_value=self.site.team,
		)
		switched.start()
		self.addCleanup(switched.stop)
		return SupportAccess("Support Access", self.access.name)

	def test_employee_switched_into_target_team_cannot_accept_their_own_request(self):
		access = self.act_in_site_team_as(self.employee.user)
		access.status = "Accepted"
		with self.assertRaisesRegex(frappe.ValidationError, "You don't have permission to set this status"):
			access.save()
		self.assertEqual(frappe.db.get_value("Support Access", access.name, "status"), "Pending")

	def test_system_manager_switched_into_target_team_can_accept_the_request(self):
		from press.access.test_employee_consent import create_test_employee

		access = self.act_in_site_team_as(create_test_employee("System Manager").user)
		access.status = "Accepted"
		access.save()
		self.assertEqual(frappe.db.get_value("Support Access", access.name, "status"), "Accepted")

	def test_member_of_target_team_can_accept_the_request(self):
		access = self.act_in_site_team_as(frappe.db.get_value("Team", self.site.team, "user"))
		access.status = "Accepted"
		access.save()
		self.assertEqual(frappe.db.get_value("Support Access", access.name, "status"), "Accepted")
