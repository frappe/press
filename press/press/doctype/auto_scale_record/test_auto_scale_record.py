# Copyright (c) 2025, Frappe and Contributors
# See license.txt
from __future__ import annotations

import typing
from datetime import datetime, timedelta
from typing import Literal
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from press.api.server import schedule_auto_scale
from press.press.doctype.auto_scale_record.auto_scale_record import AutoScaleRecord
from press.press.doctype.server.test_server import create_test_server

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


def mimic_memory_usage(is_high: bool = False):
	return {"memory": 0.4} if not is_high else {"memory": 0.9}


def mimic_cpu_usage(is_high: bool = False):
	return {"vcpu": 0.4} if not is_high else {"vcpu": 0.9}


def mimic_get_cpu_and_memory_usage(is_high: bool = False):
	cpu_usage = mimic_get_cpu_and_memory_usage(is_high)
	cpu_usage.update(mimic_memory_usage(is_high))
	return cpu_usage


def create_test_auto_scale_record(
	action: Literal["Scale Up", "Scale Down"],
	is_automatically_triggered: bool = False,
	server: Server | None = None,
) -> AutoScaleRecord:
	server = server or create_test_server()
	server.secondary_server = (
		create_test_server().name if not server.secondary_server else server.secondary_server
	)
	return frappe.get_doc(
		{
			"doctype": "Auto Scale Record",
			"server": server.name,
			"action": action,
			"is_automatically_triggered": is_automatically_triggered,
		}
	).insert()


@patch.object(AutoScaleRecord, "after_insert", new=Mock())
class UnitTestAutoScaleRecord(TestCase):
	"""
	Unit tests for AutoScaleRecord.
	Use this class for testing individual functions and methods.
	"""

	def test_scheduled_auto_scale(self):
		primary_server = create_test_server()
		secondary_server = create_test_server()
		primary_server.secondary_server = secondary_server.name
		primary_server.save()

		first_auto_scale_window = [
			datetime.now() + timedelta(minutes=1),
			datetime.now() + timedelta(minutes=6),
		]

		with self.assertRaises(frappe.ValidationError):
			# Scales must be atleast 60 minutes apart
			schedule_auto_scale(
				primary_server.name,
				scheduled_scale_up_time=first_auto_scale_window[0],
				scheduled_scale_down_time=first_auto_scale_window[1],
			)

		first_auto_scale_window[1] = datetime.now() + timedelta(minutes=61)
		schedule_auto_scale(
			primary_server.name,
			scheduled_scale_up_time=first_auto_scale_window[0],
			scheduled_scale_down_time=first_auto_scale_window[1],
		)

		# A scheduled auto scale cannot be created if there is a conflicting auto scale window
		# Trying to scale up when already scaled up according to the previous schedule
		conflicting_auto_scale_window = [
			datetime.now() + timedelta(minutes=5),
			datetime.now() + timedelta(minutes=70),
		]

		with self.assertRaises(frappe.ValidationError):
			# Scales must be atleast 60 minutes apart
			schedule_auto_scale(
				primary_server.name,
				scheduled_scale_up_time=conflicting_auto_scale_window[0],
				scheduled_scale_down_time=conflicting_auto_scale_window[1],
			)

		# Trying to scale up in the past
		conflicting_auto_scale_window[0] = datetime.now() + timedelta(minutes=-10)
		with self.assertRaises(frappe.ValidationError):
			schedule_auto_scale(
				primary_server.name,
				scheduled_scale_up_time=conflicting_auto_scale_window[0],
				scheduled_scale_down_time=conflicting_auto_scale_window[1],
			)
