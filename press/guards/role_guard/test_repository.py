# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.github import branches, get_installation_url, installation_repositories, options
from press.press.doctype.github_installation.github_installation import link_installations
from press.press.doctype.github_installation.test_github_installation import (
	make_installation,
	make_response,
)
from press.press.doctype.press_role.press_role import REPOSITORY
from press.press.doctype.press_role.test_press_role import create_permission_role, create_user
from press.press.doctype.team.test_team import create_test_team


def make_repository(name: str) -> dict:
	return {"id": 1, "name": name, "private": True, "html_url": "url", "default_branch": "main"}


class TestRoleRepositoryAccess(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		frappe.db.set_value("Team", self.team.name, "github_installations_enabled", 1)
		self.link([make_installation(11, 101, "acme"), make_installation(12, 102, "beta")])
		self.member = create_user(f"{frappe.generate_hash(length=8)}@example.com").name
		self.team.append("team_members", {"user": self.member})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.add_user(self.member)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_new_role_grants_all_repositories(self):
		self.assertEqual(self.role.all_repositories, 1)

		with self.as_member(), self.github(["app", "other"]):
			repositories = installation_repositories("11")

		self.assertEqual([row["name"] for row in repositories], ["app", "other"])

	def test_options_for_restricted_member_lists_only_accounts_with_a_granted_repository(self):
		self.restrict_to("acme/app")

		with self.as_member():
			data = options()

		self.assertEqual([installation["login"] for installation in data["installations"]], ["acme"])
		self.assertTrue(data["restricted"])

	def test_options_for_member_whose_role_grants_no_repository_is_restricted_and_empty(self):
		self.role.all_repositories = 0
		self.role.save()

		with self.as_member():
			data = options()

		self.assertEqual((data["installations"], data["restricted"]), ([], True))

	def test_options_for_member_with_all_repositories_is_not_restricted(self):
		with self.as_member():
			data = options()

		self.assertEqual(len(data["installations"]), 2)
		self.assertFalse(data["restricted"])

	def test_restricted_member_cannot_start_connecting_github(self):
		self.restrict_to("acme/app")

		with (
			self.as_member(),
			self.assertRaisesRegex(frappe.PermissionError, "can't connect GitHub accounts"),
		):
			get_installation_url()

	def test_member_with_all_repositories_can_start_connecting_github(self):
		with self.as_member():
			data = get_installation_url()

		self.assertTrue(data["state"])

	def test_member_of_team_without_roles_can_start_connecting_github(self):
		frappe.delete_doc("Press Role", self.role.name, force=True)

		with self.as_member():
			data = get_installation_url()

		self.assertTrue(data["state"])

	def test_installation_repositories_for_restricted_member_lists_only_granted_repositories(self):
		self.restrict_to("acme/app")

		with self.as_member(), self.github(["App", "other"]):
			repositories = installation_repositories("11")

		self.assertEqual([row["name"] for row in repositories], ["App"])

	def test_branches_rejects_a_repository_the_members_role_does_not_grant(self):
		self.restrict_to("acme/app")

		with (
			self.as_member(),
			patch("press.api.github.get_branches") as get_branches,
			self.assertRaisesRegex(frappe.PermissionError, "access to the repository acme/other"),
		):
			branches("acme", "other", installation="11")

		get_branches.assert_not_called()

	def test_branches_allows_a_repository_the_members_role_grants(self):
		self.restrict_to("acme/app")

		with self.as_member(), patch("press.api.github.get_branches", return_value=[]) as get_branches:
			branches("acme", "app", installation="11")

		get_branches.assert_called_once_with("acme", "app", "11")

	def test_release_group_add_app_rejects_a_repository_the_members_role_does_not_grant(self):
		self.restrict_to("acme/app")
		group = frappe.get_doc({"doctype": "Release Group", "team": self.team.name})
		app = {
			"name": "other_app",
			"title": "Other App",
			"repository_url": "https://github.com/acme/other",
			"branch": "main",
			"github_installation_id": "11",
		}

		with self.as_member(), self.assertRaisesRegex(frappe.PermissionError, "repository acme/other"):
			group.add_app(app)

		self.assertFalse(frappe.db.exists("App", "other_app"))

	def test_add_resource_stores_repository_with_its_installation_and_remove_resource_drops_it(self):
		self.role.add_resource([{"document_type": REPOSITORY, "document_name": "acme/app"}])
		self.assertEqual(
			[(row.repository, row.github_installation) for row in self.role.repositories],
			[("acme/app", self.installation_name("11"))],
		)

		self.role.remove_resource(REPOSITORY, "acme/app")
		self.assertEqual(self.role.repositories, [])

	def test_add_resource_rejects_repository_of_an_account_not_linked_to_the_team(self):
		with self.assertRaisesRegex(frappe.ValidationError, "isn't in a GitHub account connected"):
			self.role.add_resource([{"document_type": REPOSITORY, "document_name": "stranger/app"}])

		self.role.reload()
		self.assertEqual(self.role.repositories, [])

	def restrict_to(self, repository: str):
		self.role.all_repositories = 0
		self.role.save()
		self.role.add_resource([{"document_type": REPOSITORY, "document_name": repository}])

	def installation_name(self, installation_id: str) -> str:
		filters = {"team": self.team.name, "installation_id": installation_id}
		return frappe.db.get_value("GitHub Installation", filters)

	def link(self, installations: list[dict]):
		with patch(
			"press.api.github.requests.get", return_value=make_response({"installations": installations})
		):
			link_installations(self.team.name, "user-token")

	@contextmanager
	def github(self, names: list[str]):
		response = make_response({"repositories": [make_repository(name) for name in names]})
		with (
			patch("press.api.github.get_access_token", return_value="installation-token"),
			patch("press.api.github.requests.get", return_value=response),
		):
			yield

	@contextmanager
	def as_member(self):
		frappe.set_user(self.member)
		frappe.local.request = frappe._dict(method="POST", headers={"X-Press-Team": self.team.name})
		try:
			yield
		finally:
			del frappe.local.request
			frappe.set_user("Administrator")
