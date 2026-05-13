# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.test import foreground_enqueue, foreground_enqueue_doc


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.enqueue", new=foreground_enqueue)
@patch("frappe.db.commit", new=lambda: None)
class TestPressWorkflowTestDoctype(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")

	def tearDown(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")

	def test_create_workflow_test_doc(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 10,
				"input_b": 5,
			}
		).insert()

		self.assertEqual(doc.input_a, 10)
		self.assertEqual(doc.input_b, 5)
		doc.delete()

	def test_workflow_test_sample_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		result = doc.sample_task()
		self.assertEqual(result, "task done")
		doc.delete()

	def test_workflow_test_sample_failing_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		with self.assertRaises(ValueError) as ctx:
			doc.sample_failing_task()
		self.assertIn("task failed", str(ctx.exception))
		doc.delete()

	def test_workflow_test_add_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 10,
				"input_b": 20,
			}
		).insert()

		result = doc.add(10, 20)
		self.assertEqual(result, 30)
		doc.delete()

	def test_workflow_test_multiply_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 3,
				"input_b": 4,
			}
		).insert()

		result = doc.multiply(3, 4)
		self.assertEqual(result, 12)
		doc.delete()

	def test_workflow_test_power_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 2,
				"input_b": 3,
			}
		).insert()

		result = doc.power(2, 3)
		self.assertEqual(result, 8)
		doc.delete()

	def test_workflow_test_noisy_task(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		result = doc.noisy_task()
		self.assertEqual(result, "done")
		doc.delete()

	def test_workflow_test_main_success_flow(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		result = doc.main_success()
		self.assertEqual(result, "success output")
		doc.delete()

	def test_workflow_test_main_fail_flow(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		with self.assertRaises(ValueError):
			doc.main_fail()
		doc.delete()

	def test_workflow_test_skipped_steps_flow(self):
		doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 1,
				"input_b": 2,
			}
		).insert()

		result = doc.skipped_steps_flow()
		self.assertEqual(result, "skipped")
		doc.delete()
