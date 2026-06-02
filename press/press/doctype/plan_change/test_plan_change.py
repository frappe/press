# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for plan_change/plan_change.py.

PlanChange.validate() is exercised with mocked frappe.db.get_value so that no
real Server / Server Plan documents are required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.plan_change.plan_change import PlanChange

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

_MODULE = "press.press.doctype.plan_change.plan_change"


def _doc(
	from_plan: str | None = None,
	to_plan: str = "plan-b",
	plan_type: str = "",
	document_type: str = "Server",
	document_name: str = "test-srv",
) -> SimpleNamespace:
	"""Return a SimpleNamespace that mimics a PlanChange document."""
	return SimpleNamespace(
		document_type=document_type,
		document_name=document_name,
		from_plan=from_plan,
		to_plan=to_plan,
		type=plan_type,
		team=None,
	)


# ══════════════════════════════════════════════════════════════════════════════
# PlanChange.validate — team population
# ══════════════════════════════════════════════════════════════════════════════


class TestPlanChangeValidateTeam(FrappeTestCase):
	"""validate() always fetches and sets team from the linked document."""

	@patch(f"{_MODULE}.frappe.db.get_value", return_value="team-alpha")
	def test_team_populated_from_document(self, _mock):
		doc = _doc()
		PlanChange.validate(doc)
		self.assertEqual(doc.team, "team-alpha")

	@patch(f"{_MODULE}.frappe.db.get_value", return_value=None)
	def test_team_is_none_when_document_has_no_team(self, _mock):
		"""Edge case: linked document has no team field (returns None)."""
		doc = _doc()
		PlanChange.validate(doc)
		self.assertIsNone(doc.team)


# ══════════════════════════════════════════════════════════════════════════════
# PlanChange.validate — upgrade / downgrade detection
# ══════════════════════════════════════════════════════════════════════════════


class TestPlanChangeValidateType(FrappeTestCase):
	"""validate() infers type='Upgrade' or 'Downgrade' from price comparison."""

	def _gv_factory(self, from_price: float, to_price: float):
		"""Return a side_effect for frappe.db.get_value with plan price mapping."""

		def _gv(doctype, name, field):
			if doctype != "Server Plan":
				return "team-1"
			return from_price if name == "plan-a" else to_price

		return _gv

	def test_upgrade_when_to_plan_is_more_expensive(self):
		doc = _doc(from_plan="plan-a", to_plan="plan-b", plan_type="")
		with patch(f"{_MODULE}.frappe.db.get_value", side_effect=self._gv_factory(10.0, 20.0)):
			PlanChange.validate(doc)
		self.assertEqual(doc.type, "Upgrade")

	def test_downgrade_when_to_plan_is_cheaper(self):
		doc = _doc(from_plan="plan-a", to_plan="plan-b", plan_type="")
		with patch(f"{_MODULE}.frappe.db.get_value", side_effect=self._gv_factory(20.0, 10.0)):
			PlanChange.validate(doc)
		self.assertEqual(doc.type, "Downgrade")

	def test_type_not_changed_when_already_set(self):
		"""If type is already explicitly set, validate() must not overwrite it."""
		doc = _doc(from_plan="plan-a", to_plan="plan-b", plan_type="Upgrade")
		with patch(f"{_MODULE}.frappe.db.get_value", return_value="team-1"):
			PlanChange.validate(doc)
		self.assertEqual(doc.type, "Upgrade")

	def test_no_type_detection_without_from_plan(self):
		"""When from_plan is absent, type stays empty — no price DB call is made."""
		doc = _doc(from_plan=None, to_plan="plan-b", plan_type="")
		with patch(f"{_MODULE}.frappe.db.get_value", return_value="team-1") as mock_gv:
			PlanChange.validate(doc)
		# frappe.db.get_value should only be called once (for team lookup)
		self.assertEqual(mock_gv.call_count, 1)
		self.assertEqual(doc.type, "")

	def test_equal_prices_detected_as_upgrade(self):
		"""When prices are equal, the condition from > to is False → type = 'Upgrade'."""
		doc = _doc(from_plan="plan-a", to_plan="plan-b", plan_type="")
		with patch(f"{_MODULE}.frappe.db.get_value", side_effect=self._gv_factory(15.0, 15.0)):
			PlanChange.validate(doc)
		self.assertEqual(doc.type, "Upgrade")


# ══════════════════════════════════════════════════════════════════════════════
# PlanChange.validate — Initial Plan handling
# ══════════════════════════════════════════════════════════════════════════════


class TestPlanChangeValidateInitialPlan(FrappeTestCase):
	"""validate() clears from_plan when type is 'Initial Plan'."""

	@patch(f"{_MODULE}.frappe.db.get_value", return_value="team-1")
	def test_from_plan_cleared_for_initial_plan(self, _mock):
		doc = _doc(from_plan="plan-x", plan_type="Initial Plan")
		PlanChange.validate(doc)
		self.assertEqual(doc.from_plan, "")

	@patch(f"{_MODULE}.frappe.db.get_value", return_value="team-1")
	def test_from_plan_not_cleared_for_upgrade(self, _mock):
		"""Only 'Initial Plan' clears from_plan; Upgrade should not."""
		doc = _doc(from_plan="plan-x", plan_type="Upgrade")
		PlanChange.validate(doc)
		self.assertEqual(doc.from_plan, "plan-x")
