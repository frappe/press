# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import typing
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.bench import get_release_group_policy_for_bench
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.test_release_group import create_test_release_group

if typing.TYPE_CHECKING:
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.release_group_policy.release_group_policy import ReleaseGroupPolicy


class TestReleaseGroupPolicy(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		# App creation
		cls.frappe_app = create_test_app("frappe")
		cls.erpnext_app = create_test_app("erpnext")

		# App source creation
		cls.frappe_app_sources_one = create_test_app_source(
			"Version 16", cls.frappe_app, "https://github.com/frappe/frappe", branch="version-16"
		)
		cls.frappe_app_sources_two = create_test_app_source(
			"Nightly", cls.frappe_app, "https://github.com/frappe/frappe", branch="develop"
		)
		cls.erpnext_app_sources_one = create_test_app_source(
			"Version 16", cls.erpnext_app, "https://github.com/frappe/erpnext", branch="version-16"
		)
		cls.erpnext_app_sources_two = create_test_app_source(
			"Nightly", cls.erpnext_app, "https://github.com/frappe/erpnext", branch="develop"
		)

		# App release creation with random unique hashes
		for _ in range(5):  # Generate 5 unique hashes everyone gets 5 releases
			random_hash = uuid.uuid4().hex
			create_test_app_release(cls.frappe_app_sources_one, random_hash)
			create_test_app_release(cls.frappe_app_sources_two, random_hash)
			create_test_app_release(cls.erpnext_app_sources_one, random_hash)
			create_test_app_release(cls.erpnext_app_sources_two, random_hash)

	def test_auto_app_addition_from_policies(self):
		release_group: ReleaseGroup = create_test_release_group(
			[self.frappe_app], frappe_version="Version 16", app_sources=[self.frappe_app_sources_one.name]
		)

		# We have no policy set for this release group yet, so it should not have any mandatory apps
		self.assertEqual(get_release_group_policy_for_bench(release_group.version), {"policies": []})

		# Now we will add a policy for the release group that mandates the erpnext app with specific version and source
		release_group_policies: ReleaseGroupPolicy = frappe.get_doc(
			{
				"doctype": "Release Group Policy",
				"scope": "Frappe Version",
				"target": "Version 16",
				"status": "Active",
				"policy_name": "Version 16 Bundle Policy",
			}
		)
		release_group_policies.append(
			"policies",
			{"app": self.erpnext_app.name, "source": self.erpnext_app_sources_one.name, "add_on_creation": 1},
		)
		release_group_policies.insert()

		# Now when we fetch the policies for the release group, it should reflect the newly added policy
		self.assertEqual(
			get_release_group_policy_for_bench(release_group.version),
			{
				"policies": [
					{
						"app": self.erpnext_app.name,
						"source": self.erpnext_app_sources_one.name,
					}
				]
			},
		)

		self.assertEqual(
			get_release_group_policy_for_bench("Version 15"),
			{"policies": []},
		)
