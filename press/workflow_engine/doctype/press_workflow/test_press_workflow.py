# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.test import foreground_enqueue, foreground_enqueue_doc

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.press_workflow import (
		PressWorkflow,
	)
	from press.workflow_engine.doctype.press_workflow_test.press_workflow_test import (
		PressWorkflowTest,
	)


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.enqueue", new=foreground_enqueue)
@patch("frappe.db.commit", new=lambda: None)  # No-op commit to avoid issues with transactions in tests
class IntegrationTestPressWorkflow(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")
		self.doc: PressWorkflowTest = frappe.get_doc(
			{
				"doctype": "Press Workflow Test",
				"input_a": 3,
				"input_b": 2,
			}
		)  # type: ignore
		self.doc.insert()

	def tearDown(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")
		self.doc.delete()

	def get_wf(self, workflow_name: str) -> "PressWorkflow":
		wf = frappe.get_doc("Press Workflow", workflow_name)
		wf.reload()
		return wf  # type: ignore

	def test_workflow_success(self):
		wf = self.get_wf(self.doc.main_success.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "success output")

	def test_workflow_fail(self):
		wf = self.get_wf(self.doc.main_fail.run_as_workflow())
		self.assertEqual(wf.status, "Failure")
		with self.assertRaises(Exception) as e:
			wf.get_result()
		self.assertTrue("mock failure" in str(e.exception))

	def test_workflow_with_task_success(self):
		wf = self.get_wf(self.doc.main_with_task.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "task done")

	def test_workflow_with_nested_task(self):
		wf = self.get_wf(self.doc.main_with_nested_task.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "task done")

	def test_workflow_with_failing_task(self):
		wf = self.get_wf(self.doc.main_with_failing_task.run_as_workflow())
		self.assertEqual(wf.status, "Failure")
		with self.assertRaises(Exception) as e:
			wf.get_result()
		self.assertTrue("task failed" in str(e.exception))

	def test_workflow_with_args_task(self):
		wf = self.get_wf(self.doc.main_with_args_task.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 5)

	def test_workflow_with_task_id_loop(self):
		wf = self.get_wf(self.doc.main_with_task_id_loop.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 9)

	def test_workflow_with_task_id_passthrough(self):
		wf = self.get_wf(self.doc.main_with_task_id_passthrough.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 9)
		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name}, pluck="stdout")
		self.assertTrue(any("power_mult_0" in str(t) for t in tasks))
		self.assertTrue(any("power_mult_1" in str(t) for t in tasks))

	def test_workflow_with_noisy_task(self):
		wf = self.get_wf(self.doc.main_with_noisy_task.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "done")

	def test_workflow_as_flow(self):
		wf = self.get_wf(self.doc.main_as_flow.run_as_workflow())
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "flow done")

	def test_flow_with_args(self):
		wf = self.get_wf(self.doc.flow_with_args.run_as_workflow(x=4, y=5))
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 9)

	def test_force_fail(self):
		with patch(
			"press.workflow_engine.doctype.press_workflow.press_workflow.enqueue_workflow",
			new=lambda *_args, **_kwargs: None,
		):
			wf = frappe.get_doc(
				{
					"doctype": "Press Workflow",
					"linked_doctype": "Press Workflow Test",
					"linked_docname": self.doc.name,
					"main_method_name": "main_success",
					"main_method_title": "Main Success",
					"status": "Queued",
				}
			).insert(ignore_permissions=True)

		wf.force_fail()
		self.assertTrue(frappe.db.get_value("Press Workflow", wf.name, "is_force_failure_requested"))

	def test_force_fail_already_completed(self):
		wf_name = self.doc.main_success.run_as_workflow()
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")

		with self.assertRaises(frappe.ValidationError):
			wf.force_fail()

	def test_on_trash_deletes_tasks(self):
		wf_name = self.doc.main_with_task.run_as_workflow()
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")

		tasks_before = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertTrue(len(tasks_before) > 0)

		wf.delete()
		tasks_after = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks_after), 0)

	def test_workflow_fatal_status(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_success",
				"main_method_title": "Main Success",
				"status": "Fatal",
				"traceback": "Test traceback",
			}
		).insert(ignore_permissions=True)

		from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowFatalError

		with self.assertRaises(PressWorkflowFatalError) as ctx:
			wf.get_result()
		self.assertIn("fatal error", str(ctx.exception).lower())
		self.assertEqual(ctx.exception.traceback, "Test traceback")

	def test_workflow_queued_running_error(self):
		with patch(
			"press.workflow_engine.doctype.press_workflow.press_workflow.enqueue_workflow",
			new=lambda *_args, **_kwargs: None,
		):
			wf = frappe.get_doc(
				{
					"doctype": "Press Workflow",
					"linked_doctype": "Press Workflow Test",
					"linked_docname": self.doc.name,
					"main_method_name": "main_success",
					"main_method_title": "Main Success",
					"status": "Queued",
				}
			).insert(ignore_permissions=True)

		from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowRunningError

		with self.assertRaises(PressWorkflowRunningError):
			wf.get_result()

		wf.reload()
		wf.status = "Running"
		wf.save()
		with self.assertRaises(PressWorkflowRunningError):
			wf.get_result()

	def test_workflow_success_with_none_output(self):
		wf_name = self.doc.main_success.run_as_workflow()
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")
		result = wf.get_result()
		self.assertEqual(result, "success output")

	def test_workflow_with_skipped_steps(self):
		wf_name = self.doc.skipped_steps_flow.run_as_workflow()
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")

		steps = wf.steps
		self.assertTrue(len(steps) > 0)
		for step in steps:
			self.assertEqual(step.status, "Skipped")

	def test_workflow_as_flow_with_multiple_tasks(self):
		wf_name = self.doc.main_as_flow.run_as_workflow()
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), "flow done")

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name}, pluck="name")
		self.assertTrue(len(tasks) >= 2)

	def test_workflow_with_kwargs(self):
		wf_name = self.doc.flow_with_args.run_as_workflow(x=10, y=20)
		wf = self.get_wf(wf_name)
		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 30)

	def test_workflow_failure_with_no_exception(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_success",
				"main_method_title": "Main Success",
				"status": "Failure",
			}
		).insert(ignore_permissions=True)

		from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowFailedError

		with self.assertRaises(PressWorkflowFailedError) as ctx:
			wf.get_result()
		self.assertIn("no exception was recorded", str(ctx.exception).lower())
