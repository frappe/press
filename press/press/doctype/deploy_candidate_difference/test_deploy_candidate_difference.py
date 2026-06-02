# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy.deploy import create_deploy_candidate_differences


@patch("press.press.doctype.deploy.deploy.frappe.db.commit", new=Mock())
def create_test_deploy_candidate_differences(*args, **kwargs):
	return create_deploy_candidate_differences(*args, **kwargs)


class TestDeployCandidateDifference(FrappeTestCase):
	"""Tests for DeployCandidateDifference.validate() guards."""

	_MODULE = "press.press.doctype.deploy_candidate_difference.deploy_candidate_difference"

	def _doc(self, source="dc-A", destination="dc-B", group="rg-1", name="DCD-1"):
		from types import SimpleNamespace

		return SimpleNamespace(
			source=source,
			destination=destination,
			group=group,
			name=name,
			apps=[],
			populate_apps_table=lambda: None,
		)

	def test_same_source_and_destination_raises(self):
		"""validate() raises when source == destination."""
		import frappe

		from press.press.doctype.deploy_candidate_difference.deploy_candidate_difference import (
			DeployCandidateDifference,
		)

		doc = self._doc(source="dc-X", destination="dc-X")
		with self.assertRaises(frappe.ValidationError):
			DeployCandidateDifference.validate(doc)

	def test_source_newer_than_destination_raises(self):
		"""validate() raises when source candidate was created after destination."""
		import frappe

		from press.press.doctype.deploy_candidate_difference.deploy_candidate_difference import (
			DeployCandidateDifference,
		)

		doc = self._doc(source="dc-new", destination="dc-old")

		# source_creation > destination_creation → invalid
		def _gv(doctype, name, field):
			return "2026-01-10" if name == "dc-new" else "2026-01-01"

		with (
			patch(f"{self._MODULE}.frappe.db.get_value", side_effect=_gv),
			patch(f"{self._MODULE}.frappe.get_all", return_value=[]),
			self.assertRaises(frappe.ValidationError),
		):
			DeployCandidateDifference.validate(doc)

	def test_duplicate_difference_raises(self):
		"""validate() raises when the same (group, source, destination) combo already exists."""
		import frappe

		from press.press.doctype.deploy_candidate_difference.deploy_candidate_difference import (
			DeployCandidateDifference,
		)

		doc = self._doc()

		# source_creation < destination_creation → order is fine
		def _gv(doctype, name, field):
			return "2026-01-01" if name == "dc-A" else "2026-01-10"

		with (
			patch(f"{self._MODULE}.frappe.db.get_value", side_effect=_gv),
			patch(f"{self._MODULE}.frappe.get_all", return_value=[{"name": "DCD-existing"}]),
			self.assertRaises(frappe.ValidationError),
		):
			DeployCandidateDifference.validate(doc)

	def test_valid_difference_passes(self):
		"""A valid difference (different source/destination, correct order, no duplicate) passes."""
		from press.press.doctype.deploy_candidate_difference.deploy_candidate_difference import (
			DeployCandidateDifference,
		)

		doc = self._doc()

		def _gv(doctype, name, field):
			return "2026-01-01" if name == "dc-A" else "2026-01-10"

		with (
			patch(f"{self._MODULE}.frappe.db.get_value", side_effect=_gv),
			patch(f"{self._MODULE}.frappe.get_all", return_value=[]),
		):
			DeployCandidateDifference.validate(doc)  # must not raise
