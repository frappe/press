# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from press.press.doctype.cloud_usage_driver.cloud_usage_driver import (
	DRIVER_BACKUP_OBJECTS,
	DRIVER_BACKUP_UPLOADED,
	by_provider,
	collect_upload_drivers,
	record,
	with_totals,
)

BUCKET_ONE = "test-backups-blr"
BUCKET_TWO = "test-backups-fra"


class TestCloudUsageDriver(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Cloud Usage Driver")
		frappe.db.delete("Remote File", {"file_path": ("like", "test-driver/%")})

	def upload(self, bucket, size, date):
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"file_name": frappe.generate_hash(length=8),
				"file_path": f"test-driver/{frappe.generate_hash(length=8)}",
				"file_size": size,
				"bucket": bucket,
				"status": "Available",
			}
		).insert()
		frappe.db.set_value("Remote File", remote_file.name, "creation", getdate(date), update_modified=False)
		return remote_file

	def driver_value(self, date, driver, scope=""):
		return frappe.db.get_value(
			"Cloud Usage Driver", {"date": date, "driver": driver, "scope": scope}, "value"
		)

	def test_uploads_are_counted_per_day_and_per_bucket(self):
		"""CloudWatch only publishes net bucket size, which cannot tell a busy day from
		a day the reaper kept up. Remote File carries its own creation date, so the
		bytes actually written are recoverable."""
		yesterday = add_days(getdate(), -1)
		self.upload(BUCKET_ONE, 1_000, yesterday)
		self.upload(BUCKET_ONE, 3_000, yesterday)
		self.upload(BUCKET_TWO, 500, yesterday)

		collect_upload_drivers(add_days(yesterday, -1), add_days(yesterday, 1))

		self.assertEqual(self.driver_value(yesterday, DRIVER_BACKUP_UPLOADED, BUCKET_ONE), 4_000)
		self.assertEqual(self.driver_value(yesterday, DRIVER_BACKUP_UPLOADED, BUCKET_TWO), 500)
		self.assertEqual(self.driver_value(yesterday, DRIVER_BACKUP_UPLOADED), 4_500)
		self.assertEqual(self.driver_value(yesterday, DRIVER_BACKUP_OBJECTS), 3)

	def test_each_day_is_kept_apart(self):
		yesterday, before = add_days(getdate(), -1), add_days(getdate(), -2)
		self.upload(BUCKET_ONE, 1_000, before)
		self.upload(BUCKET_ONE, 9_000, yesterday)

		collect_upload_drivers(add_days(before, -1), add_days(yesterday, 1))

		self.assertEqual(self.driver_value(before, DRIVER_BACKUP_UPLOADED, BUCKET_ONE), 1_000)
		self.assertEqual(self.driver_value(yesterday, DRIVER_BACKUP_UPLOADED, BUCKET_ONE), 9_000)

	def test_recollecting_a_day_replaces_it(self):
		yesterday = add_days(getdate(), -1)
		self.upload(BUCKET_ONE, 1_000, yesterday)
		collect_upload_drivers(add_days(yesterday, -1), add_days(yesterday, 1))

		self.upload(BUCKET_ONE, 2_000, yesterday)
		collect_upload_drivers(add_days(yesterday, -1), add_days(yesterday, 1))

		rows = frappe.get_all(
			"Cloud Usage Driver",
			{"date": yesterday, "driver": DRIVER_BACKUP_UPLOADED, "scope": BUCKET_ONE},
			pluck="value",
		)
		self.assertEqual(rows, [3_000])

	def test_fleet_total_is_stored_alongside_the_scopes(self):
		self.assertEqual(
			with_totals({("", "a"): 3, ("", "b"): 7}),
			[("", "", 10), ("", "a", 3), ("", "b", 7)],
		)

	def test_rows_without_a_scope_do_not_collide_with_the_total(self):
		"""A bucket or cluster left unset once wrote itself into the blank scope and
		overwrote the fleet total, which every verdict is measured against."""
		self.assertEqual(
			with_totals({("", ""): 3, ("", "b"): 7}),
			[("", "", 10), ("", "(none)", 3), ("", "b", 7)],
		)

	def test_each_provider_gets_its_own_total_as_well_as_the_fleet(self):
		"""A Hetzner volume growing says nothing about whether AWS storage should have
		grown, so each provider is judged against its own count first."""
		self.assertEqual(
			with_totals({("AWS EC2", "blr"): 10, ("Hetzner", "fsn1"): 4}),
			[
				("", "", 14),
				("AWS EC2", "", 10),
				("Hetzner", "", 4),
				("AWS EC2", "blr", 10),
				("Hetzner", "fsn1", 4),
			],
		)

	def test_recording_nothing_clears_the_day(self):
		yesterday = add_days(getdate(), -1)
		record(yesterday, DRIVER_BACKUP_UPLOADED, [("", "", 5)], "Bytes")
		record(yesterday, DRIVER_BACKUP_UPLOADED, [], "Bytes")

		self.assertFalse(
			frappe.db.exists("Cloud Usage Driver", {"date": yesterday, "driver": DRIVER_BACKUP_UPLOADED})
		)

	def test_a_driver_with_no_scope_does_not_repeat_itself(self):
		"""Machine counts have no scope of their own. Routing them through the scoped
		helper filed the same number twice, once as the provider total and once as an
		unnamed detail row."""
		self.assertEqual(
			by_provider({"AWS EC2": 266, "Hetzner": 12}),
			[("", "", 278), ("AWS EC2", "", 266), ("Hetzner", "", 12)],
		)

	def test_a_machine_with_no_provider_still_counts_towards_the_fleet(self):
		self.assertEqual(by_provider({"": 5, "Hetzner": 12}), [("", "", 17), ("Hetzner", "", 12)])
