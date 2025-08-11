import frappe
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import insert_events
from frappe.tests.utils import FrappeTestCase

from press.hooks import scheduler_events


class TestSanity(FrappeTestCase):
	def test_valid_scheduler_events(self):
		for event in insert_events(scheduler_events):
			frappe.get_attr(event)
