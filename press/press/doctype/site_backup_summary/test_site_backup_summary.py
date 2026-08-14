# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, getdate

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.press.doctype.site_backup_summary.site_backup_summary import (
	_update_backup_summaries,
	get_summarised_days,
	months_between,
	record_site_backups,
	summary_name,
)


class TestSiteBackupSummary(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site(subdomain=f"summary-{frappe.generate_hash(length=8)}")
		self.yesterday = getdate(add_days(None, -1))
		self.since = add_to_date(None, days=-2)

	def tearDown(self):
		frappe.db.rollback()

	def summarise(self):
		record_site_backups(self.site.name, self.since)

	def summarised(self, start=None, end=None) -> dict:
		return get_summarised_days(self.site.name, start or self.yesterday, end or self.yesterday)

	def test_a_backup_is_summarised_under_the_month_it_ran_in(self):
		create_test_site_backup(self.site.name, creation=self.yesterday)

		self.summarise()

		month = str(self.yesterday)[:7]
		self.assertTrue(frappe.db.exists("Site Backup Summary", summary_name(self.site.name, month)))

	def test_the_summary_answers_for_a_day_whose_backup_record_is_gone(self):
		backup = create_test_site_backup(self.site.name, creation=self.yesterday)
		self.summarise()

		frappe.db.delete("Site Backup", {"name": backup.name})

		day = self.summarised()[str(self.yesterday)]
		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 1024)

	def test_a_summarised_day_remembers_the_sizes_press_recorded(self):
		backup = create_test_site_backup(self.site.name, creation=self.yesterday)
		frappe.db.set_value("Site Backup", backup.name, "database_size", 2048)

		self.summarise()

		self.assertEqual(self.summarised()[str(self.yesterday)]["database"], 2048)

	def test_a_later_expiry_is_written_over_the_day_already_summarised(self):
		backup = create_test_site_backup(self.site.name, creation=self.yesterday)
		self.summarise()
		self.assertEqual(self.summarised()[str(self.yesterday)]["files"], "Stored")

		frappe.db.set_value(
			"Site Backup",
			backup.name,
			{
				"files_availability": "Unavailable",
				"files_expired_on": frappe.utils.now_datetime(),
				"retention_rule": "Daily",
			},
		)
		self.summarise()

		day = self.summarised()[str(self.yesterday)]
		self.assertEqual(day["files"], "Deleted")
		self.assertEqual(day["rule"], "Daily")

	def test_a_day_outside_the_asked_range_is_left_out(self):
		create_test_site_backup(self.site.name, creation=self.yesterday)
		self.summarise()

		older = add_days(self.yesterday, -5)
		self.assertEqual(self.summarised(older, older), {})

	def test_summarising_again_keeps_the_days_already_stored(self):
		older = add_days(self.yesterday, -20)
		create_test_site_backup(self.site.name, creation=older)
		record_site_backups(self.site.name, add_to_date(None, days=-30))

		create_test_site_backup(self.site.name, creation=self.yesterday)
		self.summarise()

		self.assertIn(str(older), self.summarised(older, self.yesterday))
		self.assertIn(str(self.yesterday), self.summarised(older, self.yesterday))

	@patch("press.press.doctype.site_backup_summary.site_backup_summary.frappe.db.commit", new=MagicMock())
	def test_the_nightly_pass_summarises_the_sites_whose_backups_changed(self):
		create_test_site_backup(self.site.name, creation=self.yesterday)

		_update_backup_summaries()

		self.assertIn(str(self.yesterday), self.summarised())

	def test_a_day_the_site_was_never_backed_up_on_is_not_summarised(self):
		create_test_site_backup(self.site.name, creation=self.yesterday)

		self.summarise()

		self.assertNotIn(str(getdate()), self.summarised(self.yesterday, getdate()))

	def test_another_sites_summary_is_not_read(self):
		"""A between on the text month folds the site filter into itself and answers for everyone."""
		other = create_test_site(subdomain=f"summary-other-{frappe.generate_hash(length=8)}")
		create_test_site_backup(other.name, creation=self.yesterday)
		record_site_backups(other.name, self.since)

		self.assertEqual(self.summarised(), {})

	def test_a_range_spanning_months_reads_every_month(self):
		older = add_days(self.yesterday, -45)
		create_test_site_backup(self.site.name, creation=older)
		create_test_site_backup(self.site.name, creation=self.yesterday)
		record_site_backups(self.site.name, add_to_date(None, days=-60))

		summarised = self.summarised(older, self.yesterday)

		self.assertIn(str(older), summarised)
		self.assertIn(str(self.yesterday), summarised)

	def test_a_range_inside_one_month_asks_for_that_month_alone(self):
		self.assertEqual(months_between(getdate("2026-02-03"), getdate("2026-02-27")), ["2026-02"])

	def test_a_range_over_a_year_end_lists_the_months_in_order(self):
		self.assertEqual(
			months_between(getdate("2025-11-30"), getdate("2026-02-01")),
			["2025-11", "2025-12", "2026-01", "2026-02"],
		)
