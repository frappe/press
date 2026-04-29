# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.test import foreground_enqueue, foreground_enqueue_doc
from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow.workflow_builder import (
	ensure_to_resolve_context,
)
from press.workflow_engine.doctype.press_workflow_kv.press_workflow_kv import (
	InMemoryKVStore,
	WorkflowKVStore,
)


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.enqueue", new=foreground_enqueue)
@patch("frappe.db.commit", new=lambda: None)
class TestWorkflowBuilder(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Press Workflow")
		frappe.db.delete("Press Workflow Task")
		frappe.db.delete("Press Workflow Object")
		frappe.db.delete("Press Workflow KV")
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
		frappe.db.delete("Press Workflow KV")
		self.doc.delete()

	def test_kv_property_in_memory_default(self):
		kv = self.doc.kv
		self.assertIsInstance(kv, InMemoryKVStore)

	def test_kv_property_set_and_get_in_memory(self):
		self.doc.kv.set("test_key", "test_value")
		self.assertEqual(self.doc.kv.get("test_key"), "test_value")

	def test_kv_property_delete_in_memory(self):
		self.doc.kv.set("test_key", "test_value")
		self.doc.kv.delete("test_key")
		self.assertIsNone(self.doc.kv.get("test_key"))

	def test_kv_property_workflow_store(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_success",
				"main_method_title": "Main Success",
			}
		).insert(ignore_permissions=True)

		self.doc.workflow_name = wf.name
		self.doc.kv_store_type = "workflow_store"
		self.doc.kv_store_reference = None

		kv = self.doc.kv
		self.assertIsInstance(kv, WorkflowKVStore)

	def test_resolve_context_with_workflow_name(self):
		self.doc.workflow_name = "test-workflow-123"
		self.doc.resolve_context()
		self.assertEqual(self.doc.workflow_name, "test-workflow-123")

	def test_resolve_context_with_frappe_flag(self):
		self.addCleanup(lambda: frappe.flags.pop("current_press_workflow", None))
		frappe.flags.current_press_workflow = "test-workflow-from-flag"

		self.doc.workflow_name = None
		self.doc.resolve_context()

		self.assertEqual(self.doc.workflow_name, "test-workflow-from-flag")
		del frappe.flags.current_press_workflow

	def test_resolve_context_without_workflow(self):
		self.doc.workflow_name = None
		self.doc.resolve_context()

		self.assertIsNone(self.doc.workflow_name)
		self.assertEqual(self.doc.kv_store_type, "in_memory")

	def test_defer_current_task_outside_workflow(self):
		self.doc.flags.in_press_workflow_execution = False
		self.doc.defer_current_task("Defer this task")

	def test_defer_current_task_inside_workflow(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_success",
				"main_method_title": "Main Success",
			}
		).insert(ignore_permissions=True)

		self.doc.workflow_name = wf.name
		self.doc.flags.in_press_workflow_execution = True
		self.doc.flags.current_press_workflow_task = "task-001"

		with self.assertRaises(PressWorkflowTaskEnqueued) as ctx:
			self.doc.defer_current_task("Please defer")
		self.assertEqual(ctx.exception.workflow_name, wf.name)
		self.assertEqual(ctx.exception.task_name, "task-001")

	def test_defer_current_task_without_task_name(self):
		wf = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Workflow Test",
				"linked_docname": self.doc.name,
				"main_method_name": "main_success",
				"main_method_title": "Main Success",
			}
		).insert(ignore_permissions=True)

		self.doc.workflow_name = wf.name
		self.doc.flags.in_press_workflow_execution = True

		with self.assertRaises(PressWorkflowTaskEnqueued) as ctx:
			self.doc.defer_current_task()
		self.assertEqual(ctx.exception.workflow_name, wf.name)
		self.assertIsNone(ctx.exception.task_name)

	def test_ensure_to_resolve_context_decorator(self):
		@ensure_to_resolve_context
		def my_method(self):
			return "resolved"

		result = my_method(self.doc)
		self.assertEqual(result, "resolved")

	def test_run_task_returns_cached_result_on_success(self):
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

		tasks = frappe.get_all("Press Workflow Task", filters={"workflow": wf.name})
		self.assertEqual(len(tasks), 1)

	def test_run_task_raises_exception_on_failure(self):
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

	def test_workflow_builder_attributes(self):
		self.assertIsNone(self.doc.workflow_name)
		self.assertIsNone(self.doc.workflow_doc)
		self.assertEqual(self.doc.kv_store_type, "in_memory")
		self.assertIsNone(self.doc.kv_store_reference)
		self.assertIsNone(self.doc.current_task_signature)

	def test_kv_store_type_change_discards_cache(self):
		self.doc.kv.set("key1", "value1")
		self.doc.kv_store_reference = InMemoryKVStore()

		self.addCleanup(lambda: frappe.flags.pop("current_press_workflow", None))
		frappe.flags.current_press_workflow = "test-wf-for-kv-change"
		self.doc.workflow_name = None
		self.doc.resolve_context()

		self.assertEqual(self.doc.kv_store_type, "workflow_store")
		self.assertIsNone(self.doc.kv_store_reference)
		del frappe.flags.current_press_workflow
