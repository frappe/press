# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from collections.abc import Callable
from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.press_workflow import (
		PressWorkflow,
	)
	from press.workflow_engine.doctype.press_workflow_test.press_workflow_test import (
		PressWorkflowTest,
	)


def foreground_enqueue_doc(
	doctype: str,
	docname: str,
	method: str,
	queue="default",
	timeout=None,
	now=False,  # default args unused to avoid them from going to kwargs
	enqueue_after_commit=False,
	job_id=None,
	deduplicate=False,
	at_front: bool = False,
	**kwargs,
):
	getattr(frappe.get_doc(doctype, docname), method)(**kwargs)


def foreground_enqueue(
	method: str | Callable,
	queue: str = "default",
	timeout: int | None = None,
	event=None,
	is_async: bool = True,
	job_name: str | None = None,
	now: bool = True,
	enqueue_after_commit: bool = False,
	*,
	on_success: Callable | None = None,
	on_failure: Callable | None = None,
	at_front: bool = False,
	job_id: str | None = None,
	deduplicate: bool = False,
	**kwargs,
):
	return frappe.call(method, **kwargs)


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
