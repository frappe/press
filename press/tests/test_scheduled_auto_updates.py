import frappe

from datetime import datetime, timedelta
from unittest import TestCase
from press.press.doctype.site_update.scheduled_auto_updates import (
	should_update_trigger_for_daily,
	should_update_trigger_for_weekly,
)

TEST_DATA_DAILY_TRUE = [
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 40),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 10, 30, 40),
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 40),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 10, 30, 40),
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 6, 30, 40),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 18, 10, 30, 40),
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 6, 30, 40),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 18, 10, 30, 40),
	}
]

TEST_DATA_DAILY_FALSE = [
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 19, 10, 30, 0),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 11, 30, 40),
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 19, 10, 30, 0),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 8, 30, 40),
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 0),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 6, 30, 40),
	}
]

TEST_DATA_WEEKLY_TRUE = [
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 0), # 10.30
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 10, 30, 3), # 10.30, Friday
		"update_on_weekday": datetime(2021, 3, 19, 6, 30, 40).strftime("%A") # Friday
	}
]


TEST_DATA_WEEKLY_FALSE = [
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 0), # 10.30
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 18, 6, 30, 40), # 6.30, Thursday
		"update_on_weekday": datetime(2021, 3, 19, 6, 30, 40).strftime("%A") # Friday
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 0), # 10.30
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 6, 30, 3), # 6.30, Friday
		"update_on_weekday": datetime(2021, 3, 19, 6, 30, 40).strftime("%A") # Friday
	},
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 19, 10, 30, 50), # 10.30, Friday
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"current_datetime": datetime(2021, 3, 19, 11, 30, 3), # 11.30, Friday
		"update_on_weekday": datetime(2021, 3, 19, 10, 30, 40).strftime("%A") # Friday
	}
]


class TestScheduledAutoUpdates(TestCase):
	def test_should_update_daily_positive(self):
		for obj in TEST_DATA_DAILY_TRUE:
			self.assertTrue(
				should_update_trigger_for_daily(frappe._dict(obj), obj["current_datetime"]),
				obj
			)

	def test_should_update_daily_negative(self):
		for obj in TEST_DATA_DAILY_FALSE:
			self.assertFalse(
				should_update_trigger_for_daily(frappe._dict(obj), obj["current_datetime"]),
				obj
			)
	
	def test_should_trigger_weekly_positive(self):
		for obj in TEST_DATA_WEEKLY_TRUE:
			self.assertTrue(
				should_update_trigger_for_weekly(frappe._dict(obj), obj["current_datetime"]),
				obj
			)
	
	def test_should_trigger_weekly_negative(self):
		for obj in TEST_DATA_WEEKLY_FALSE:
			self.assertFalse(
				should_update_trigger_for_weekly(frappe._dict(obj), obj["current_datetime"]),
				obj
			)