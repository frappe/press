import frappe

from datetime import datetime, timedelta
from unittest import TestCase
from press.press.doctype.site_update.scheduled_auto_updates import (
	should_update_trigger_for_daily,
)

TEST_DATA_DAILY_TRUE = [
	{
		"auto_update_last_triggered_on": datetime(2021, 3, 18, 10, 30, 40),
		"update_trigger_time": timedelta(seconds=10.5 * 60 * 60),  # 10.30
		"update_trigger_frequency": "Daily",
		"current_datetime": datetime(2021, 3, 19, 10, 30, 40),
	}
]


class TestScheduledAutoUpdates(TestCase):
	def test_should_update_daily_positive(self):
		for obj in TEST_DATA_DAILY_TRUE:
			should_update_trigger_for_daily(frappe._dict(obj), obj["current_datetime"])
