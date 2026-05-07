# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy.deploy import create_deploy_candidate_differences
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.team.test_team import create_test_team


@patch("press.press.doctype.deploy.deploy.frappe.db.commit", new=Mock())
def create_test_deploy_candidate_differences(*args, **kwargs):
	return create_deploy_candidate_differences(*args, **kwargs)


class TestDeployCandidateDifferenceValidate(FrappeTestCase):
	"""DeployCandidateDifference.validate enforces three invariants before a diff
	record is saved:

	1. Source != destination — a self-diff makes the pipeline think nothing changed.
	2. Source must be older than destination — a reversed diff computes changes backwards.
	3. No duplicate (group, source, destination) triple — duplicates cause double-migrate.
	"""

	def setUp(self):
		super().setUp()
		from press.press.doctype.deploy_candidate.test_deploy_candidate import create_test_deploy_candidate

		frappe.set_user("Administrator")
		self.team = create_test_team()
		self.app = create_test_app()
		self.rg = create_test_release_group([self.app])
		self.dc1 = create_test_deploy_candidate(self.rg)
		self.dc2 = create_test_deploy_candidate(self.rg)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _diff(self, source, destination, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Deploy Candidate Difference",
				"group": self.rg.name,
				"team": self.team.name,
				"source": source,
				"destination": destination,
				**kwargs,
			}
		).insert(ignore_permissions=True)

	def test_same_source_and_destination_raises(self):
		with self.assertRaises(frappe.ValidationError):
			self._diff(source=self.dc1.name, destination=self.dc1.name)

	def test_source_newer_than_destination_raises(self):
		# dc2 was created after dc1, so using dc2 as source violates the ordering rule
		with self.assertRaises(frappe.ValidationError):
			self._diff(source=self.dc2.name, destination=self.dc1.name)

	def test_valid_source_older_than_destination_succeeds(self):
		doc = self._diff(source=self.dc1.name, destination=self.dc2.name)
		self.assertIsNotNone(doc.name)

	def test_duplicate_diff_raises(self):
		self._diff(source=self.dc1.name, destination=self.dc2.name)
		with self.assertRaises(frappe.ValidationError):
			self._diff(source=self.dc1.name, destination=self.dc2.name)
