import frappe
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import insert_events
from press.hooks import scheduler_events
import unittest


class TestSanity(unittest.TestCase):
	def test_valid_scheduler_events(self):
		for event in insert_events(scheduler_events):
			frappe.get_attr(event)
