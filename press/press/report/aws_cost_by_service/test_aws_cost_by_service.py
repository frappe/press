# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from press.press.report.aws_cost_by_service.aws_cost_by_service import (
	build_tree_rows,
	get_columns,
	get_months,
	month_fieldname,
)


def cost_by_service(months, storage, requests):
	"""The nested {service: {usage type: {month: cost}}} a two-dimension Cost Explorer
	query comes back as."""
	previous, complete, partial = str(months[-3]), str(months[-2]), str(months[-1])
	return {
		"AmazonS3": {
			"APS3-TimedStorage-ByteHrs": dict(zip([previous, complete, partial], storage, strict=True)),
			"APS3-Requests-Tier1": dict(zip([previous, complete, partial], requests, strict=True)),
		}
	}


class TestAWSCostByService(FrappeTestCase):
	def test_change_is_measured_between_two_complete_months(self):
		"""The newest month in the window is only billed up to today. Measured against a
		whole month it reported every service as collapsing, and the notable-change flag
		fired on all of them."""
		months = get_months(6)

		service = build_tree_rows(cost_by_service(months, [100, 130, 20], [0, 0, 0]), months)[0]

		self.assertEqual(service["indent"], 0)
		self.assertAlmostEqual(service["change_amount"], 30)
		self.assertAlmostEqual(service["change_percent"], 30)
		self.assertTrue(service["notable_change"])

	def test_a_steady_service_is_not_flagged_because_the_month_is_young(self):
		months = get_months(6)

		service = build_tree_rows(cost_by_service(months, [100, 101, 8], [0, 0, 0]), months)[0]

		self.assertFalse(service["notable_change"])

	def test_the_breakdown_rows_are_measured_the_same_way(self):
		"""A child that reads as collapsing while its parent reads as steady would make
		the drill-down contradict the row it opened from."""
		months = get_months(6)

		rows = build_tree_rows(cost_by_service(months, [100, 130, 20], [40, 41, 3]), months)
		children = {row["service"]: row for row in rows if row["indent"] == 1}

		self.assertAlmostEqual(children["APS3-TimedStorage-ByteHrs"]["change_percent"], 30)
		self.assertAlmostEqual(children["APS3-Requests-Tier1"]["change_percent"], 2.5)
		self.assertFalse(children["APS3-Requests-Tier1"]["notable_change"])

	def test_rows_are_ordered_by_the_month_in_progress(self):
		"""The change column ignores the part month, but someone opening the report
		still wants the biggest spend right now at the top."""
		months = get_months(6)
		nested = cost_by_service(months, [100, 130, 20], [40, 41, 300])

		rows = build_tree_rows(nested, months)
		children = [row["service"] for row in rows if row["indent"] == 1]

		self.assertEqual(children[0], "APS3-Requests-Tier1")

	def test_the_partial_month_is_still_shown_and_labelled(self):
		months = get_months(6)

		labels = {column["fieldname"]: column["label"] for column in get_columns(months, "Usage Type")}

		self.assertIn("(MTD)", labels[month_fieldname(months[-1])])
		self.assertNotIn("(MTD)", labels[month_fieldname(months[-2])])

	def test_the_window_always_holds_the_two_months_being_compared(self):
		self.assertEqual(len(get_months(1)), 3)
		self.assertEqual(len(get_months(12)), 12)
