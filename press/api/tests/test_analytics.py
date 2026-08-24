# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from datetime import datetime, timedelta

from frappe.tests.utils import FrappeTestCase
from pytz import timezone as pytz_timezone

from press.api.analytics import align_to_quarter_hour

TIMEZONE = "Asia/Kolkata"


class TestAlignToQuarterHour(FrappeTestCase):
	def local(self, hour: int, minute: int) -> datetime:
		return pytz_timezone(TIMEZONE).localize(datetime(2026, 8, 24, hour, minute))

	def test_range_that_crosses_the_hour_keeps_start_before_end(self):
		"""A range like 10:50-10:55 used to align start after end, and prometheus answered with an error"""
		start, end = align_to_quarter_hour(self.local(10, 50), self.local(10, 55), TIMEZONE)
		self.assertEqual(start, self.local(10, 45))
		self.assertEqual(end, self.local(11, 0))

	def test_range_widens_to_the_marks_around_it(self):
		start, end = align_to_quarter_hour(self.local(10, 5), self.local(10, 20), TIMEZONE)
		self.assertEqual(start, self.local(10, 0))
		self.assertEqual(end, self.local(10, 30))

	def test_aligned_end_moves_to_the_next_mark(self):
		_, end = align_to_quarter_hour(self.local(10, 0), self.local(10, 15), TIMEZONE)
		self.assertEqual(end, self.local(10, 30))

	def test_every_minute_of_the_hour_gives_a_range_of_whole_quarters(self):
		for minute in range(60):
			for length in (1, 5, 15, 30, 59):
				original_start = self.local(10, 0) + timedelta(minutes=minute)
				original_end = original_start + timedelta(minutes=length)
				start, end = align_to_quarter_hour(original_start, original_end, TIMEZONE)
				self.assertLessEqual(start, original_start)
				self.assertGreaterEqual(end, original_end)
				self.assertEqual((end - start).total_seconds() % 900, 0)
