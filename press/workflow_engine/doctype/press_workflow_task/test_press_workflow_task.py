# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.test import foreground_enqueue, foreground_enqueue_doc


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.enqueue", new=foreground_enqueue)
@patch("frappe.db.commit", new=lambda: None)
class TestPressWorkflowTask(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")
		self.doc = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 3,
				"input_b": 2,
			}
		).insert()

	def tearDown(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")
		self.doc.delete()

	def test_task_after_insert_enqueues(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_task",
				"main_method_title": "Main With Task",
				"steps": [
					{
						"step_title": "Sample Task",
						"step_method": "sample_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()
		self.assertEqual(wf.status, "Success")

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks), 1)

		task = frappe.get_doc("Press Workflow Task", tasks[0].name)
		self.assertEqual(task.status, "Success")
		self.assertEqual(task.method_name, "sample_task")

	def test_task_update_tracked_step_status(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_task",
				"main_method_title": "Main With Task",
				"steps": [
					{
						"step_title": "Sample Task",
						"step_method": "sample_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		step = frappe.get_doc("Press Workflow Step", {"parent": wf.name})
		self.assertEqual(step.status, "Success")

	def test_task_failure_status(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_failing_task",
				"main_method_title": "Main With Failing Task",
				"steps": [
					{
						"step_title": "Sample Failing Task",
						"step_method": "sample_failing_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()
		self.assertEqual(wf.status, "Failure")

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks), 1)

		task = frappe.get_doc("Press Workflow Task", tasks[0].name)
		self.assertEqual(task.status, "Failure")
		self.assertIsNotNone(task.exception)

	def test_task_with_args_and_kwargs(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_args_task",
				"main_method_title": "Main With Args Task",
				"steps": [
					{
						"step_title": "Add",
						"step_method": "add",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 5)

	def test_task_with_nested_task(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_nested_task",
				"main_method_title": "Main With Nested Task",
				"steps": [
					{
						"step_title": "Sample Nested Task",
						"step_method": "sample_nested_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()
		self.assertEqual(wf.status, "Success")

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name}, pluck="name")
		self.assertTrue(len(tasks) >= 2)

		child_task = frappe.get_doc("Press Workflow Task", tasks[0])
		if child_task.method_name == "sample_nested_task":
			self.assertIsNotNone(child_task.parent_task)

	def test_task_resume_workflow_on_success(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_task",
				"main_method_title": "Main With Task",
				"steps": [
					{
						"step_title": "Sample Task",
						"step_method": "sample_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()
		self.assertEqual(wf.status, "Success")

	def test_task_signature_deduplication(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_args_task",
				"main_method_title": "Main With Args Task",
				"steps": [
					{
						"step_title": "Add",
						"step_method": "add",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks), 1)

		task = frappe.get_doc("Press Workflow Task", tasks[0].name)
		self.assertIsNotNone(task.signature)

	def test_task_with_queue_and_timeout(self):
		wf_name = (
			frappe.get_doc(
				{
					"doctype": "Press Workflow",
					"linked_doctype": "Press Workflow Test",
					"linked_docname": self.doc.name,
					"main_method_name": "main_success",
					"main_method_title": "Main Success",
					"steps": [],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		with patch(
			"press.workflow_engine.doctype.press_workflow_task.press_workflow_task.enqueue_task",
			return_value=None,
		):
			task_doc = frappe.new_doc("Press Workflow Task")
			task_doc.workflow = wf_name
			task_doc.method_name = "sample_task"
			task_doc.method_title = "Sample Task"
			task_doc.signature = "test-signature"
			task_doc.args_type = "tuple"
			task_doc.args = "[]"
			task_doc.kwargs_type = "dict"
			task_doc.kwargs = "{}"
			task_doc.status = "Queued"
			task_doc.queue = "long"
			task_doc.timeout = 600
			task_doc.insert(ignore_permissions=True)

		self.assertEqual(task_doc.queue, "long")
		self.assertEqual(task_doc.timeout, 600)

	def test_task_stdout_capture(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_noisy_task",
				"main_method_title": "Main With Noisy Task",
				"steps": [
					{
						"step_title": "Noisy Task",
						"step_method": "noisy_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		wf.reload()

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks), 1)

		task = frappe.get_doc("Press Workflow Task", tasks[0].name)
		self.assertIn("hello from noisy_task", task.stdout or "")

	def test_task_duration_calculation(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_with_task",
				"main_method_title": "Main With Task",
				"steps": [
					{
						"step_title": "Sample Task",
						"step_method": "sample_task",
						"status": "Pending",
					}
				],
			}
		).insert(ignore_permissions=True)

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		task = frappe.get_doc("Press Workflow Task", tasks[0].name)

		self.assertIsNotNone(task.start)
		self.assertIsNotNone(task.end)
		self.assertIsNotNone(task.duration)
