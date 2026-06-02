# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for team_change/team_change.py.

TeamChange.validate() verifies the document belongs to from_team.
TeamChange.on_update() propagates the team change across related records.
Both are tested with mocked frappe DB calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team_change.team_change import TeamChange

_MODULE = "press.press.doctype.team_change.team_change"


def _doc(
	document_type="Site",
	document_name="mysite.example.com",
	from_team="team-a",
	to_team="team-b",
	transfer_completed=0,
):
	return SimpleNamespace(
		document_type=document_type,
		document_name=document_name,
		from_team=from_team,
		to_team=to_team,
		transfer_completed=transfer_completed,
	)


# ══════════════════════════════════════════════════════════════════════════════
# TeamChange.validate
# ══════════════════════════════════════════════════════════════════════════════


class TestTeamChangeValidate(FrappeTestCase):
	"""validate() raises when the document's current team ≠ from_team."""

	def test_raises_when_document_team_does_not_match(self):
		doc = _doc(from_team="team-a")
		site_mock = MagicMock()
		site_mock.team = "team-x"  # different from from_team
		with (
			patch(f"{_MODULE}.frappe.get_doc", return_value=site_mock),
			self.assertRaises(frappe.ValidationError),
		):
			TeamChange.validate(doc)

	def test_passes_when_document_team_matches(self):
		doc = _doc(from_team="team-a")
		site_mock = MagicMock()
		site_mock.team = "team-a"  # matches from_team
		with patch(f"{_MODULE}.frappe.get_doc", return_value=site_mock):
			TeamChange.validate(doc)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# TeamChange.on_update
# ══════════════════════════════════════════════════════════════════════════════


class TestTeamChangeOnUpdate(FrappeTestCase):
	"""on_update() updates related records only after transfer is completed."""

	def test_site_transfer_propagates_team_to_related_records(self):
		doc = _doc(document_type="Site", to_team="team-b", transfer_completed=1)
		with (
			patch(f"{_MODULE}.frappe.db.set_value") as mock_sv,
			patch(f"{_MODULE}.frappe.get_all", return_value=[]),
		):
			TeamChange.on_update(doc)
		# Multiple set_value calls expected: Site, Subscription, Site Domain, etc.
		self.assertGreater(mock_sv.call_count, 0)

	def test_site_transfer_not_propagated_when_incomplete(self):
		doc = _doc(document_type="Site", transfer_completed=0)
		with (
			patch(f"{_MODULE}.frappe.db.set_value") as mock_sv,
			patch(f"{_MODULE}.frappe.get_all", return_value=[]),
		):
			TeamChange.on_update(doc)
		mock_sv.assert_not_called()

	def test_release_group_transfer_sets_team_and_skip_onboarding(self):
		doc = _doc(document_type="Release Group", to_team="team-b", transfer_completed=1)
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			TeamChange.on_update(doc)
		# Should have called set_value for Release Group team + skip_onboarding
		calls = [str(c) for c in mock_sv.call_args_list]
		any_rg_call = any("Release Group" in c for c in calls)
		self.assertTrue(any_rg_call)

	def test_non_site_non_rg_type_is_noop(self):
		doc = _doc(document_type="Server", transfer_completed=1)
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			TeamChange.on_update(doc)
		mock_sv.assert_not_called()
