# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

from press.press.report.adoption_overview.adoption_overview import execute


class TestAdoptionOverview(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def insert_daily_row(self, timestamp, group_type: str, current: int, behind: int, waiting: int = 0):
		frappe.get_doc(
			{
				"doctype": "Site Adoption Snapshot",
				"timestamp": timestamp,
				"tier": "Daily",
				"group_type": group_type,
				"current_sites": current,
				"behind_sites": behind,
				"waiting": waiting,
			}
		).insert()

	def test_rows_show_the_share_of_sites_current_per_group_type(self):
		yesterday = add_days(now_datetime(), -1)
		self.insert_daily_row(yesterday, "Public", current=3, behind=1)
		self.insert_daily_row(yesterday, "Private", current=1, behind=1)

		_, rows, *_ = execute({"from_date": add_days(today(), -2), "to_date": today()})

		percents = {row.group_type: row.percent_current for row in rows if row.timestamp == yesterday}
		self.assertEqual(percents, {"Public": 75.0, "Private": 50.0})

	def test_summary_reads_the_latest_snapshot_in_the_range(self):
		self.insert_daily_row(add_days(now_datetime(), -2), "Public", current=1, behind=9, waiting=9)
		self.insert_daily_row(add_days(now_datetime(), -1), "Public", current=9, behind=1, waiting=1)

		*_, summary = execute({"from_date": add_days(today(), -3), "to_date": today()})

		values = {card["label"]: card["value"] for card in summary}
		self.assertEqual((values["% Current"], values["Sites Behind"], values["Blocked"]), (90.0, 1, 0))
