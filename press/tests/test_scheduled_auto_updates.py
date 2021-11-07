import frappe

from unittest import TestCase
from press.press.doctype.site_update.scheduled_auto_updates import (
	should_update_trigger_for_daily,
	should_update_trigger_for_monthly,
	should_update_trigger_for_weekly,
)
from press.tests.test_data.auto_update_fixtures import (
	TEST_DATA_DAILY_TRUE,
	TEST_DATA_DAILY_FALSE,
	TEST_DATA_WEEKLY_TRUE,
	TEST_DATA_WEEKLY_FALSE,
	TEST_DATA_MONTHLY_TRUE,
	TEST_DATA_MONTHLY_FALSE,
	TEST_DATA_MONTHLY_MONTH_END,
)


class TestScheduledAutoUpdates(TestCase):
	def test_should_update_daily_positive(self):
		for obj in TEST_DATA_DAILY_TRUE:
			self.assertTrue(
				should_update_trigger_for_daily(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_update_daily_negative(self):
		for obj in TEST_DATA_DAILY_FALSE:
			self.assertFalse(
				should_update_trigger_for_daily(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_trigger_weekly_positive(self):
		for obj in TEST_DATA_WEEKLY_TRUE:
			self.assertTrue(
				should_update_trigger_for_weekly(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_trigger_weekly_negative(self):
		for obj in TEST_DATA_WEEKLY_FALSE:
			self.assertFalse(
				should_update_trigger_for_weekly(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_trigger_monthly_positive(self):
		for obj in TEST_DATA_MONTHLY_TRUE:
			self.assertTrue(
				should_update_trigger_for_monthly(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_trigger_monthly_negative(self):
		for obj in TEST_DATA_MONTHLY_FALSE:
			self.assertFalse(
				should_update_trigger_for_monthly(frappe._dict(obj), obj["current_datetime"]), obj
			)

	def test_should_trigger_month_end(self):
		for obj in TEST_DATA_MONTHLY_MONTH_END:
			self.assertTrue(
				should_update_trigger_for_monthly(frappe._dict(obj), obj["current_datetime"]), obj
			)
