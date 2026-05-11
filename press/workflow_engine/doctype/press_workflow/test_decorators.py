# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase

from press.utils.test import foreground_enqueue, foreground_enqueue_doc
from press.workflow_engine.doctype.press_workflow.decorators import (
	BoundFlow,
	_in_workflow_execution,
	flow,
	task,
)
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.enqueue", new=foreground_enqueue)
@patch("frappe.db.commit", new=lambda: None)
class TestDecorators(FrappeTestCase):
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

	def test_in_workflow_execution_true(self):
		class TestDoc(WorkflowBuilder):
			pass

		instance = TestDoc({"doctype": "Press Workflow Test"})
		instance.name = "test-name"

	def test_in_workflow_execution_false_no_workflow_name(self):
		class TestDoc(WorkflowBuilder):
			pass

		instance = TestDoc({"doctype": "Press Workflow Test"})
		instance.name = "test-name"
		instance.workflow_name = None
		instance.flags.in_press_workflow_execution = True

		self.assertFalse(_in_workflow_execution(instance))

	def test_in_workflow_execution_false_no_flag(self):
		class TestDoc(WorkflowBuilder):
			pass

		instance = TestDoc({"doctype": "Press Workflow Test"})
		instance.name = "test-name"
		instance.workflow_name = "test-workflow"
		instance.flags.in_press_workflow_execution = False

		self.assertFalse(_in_workflow_execution(instance))

	def test_in_workflow_execution_false_not_workflow_builder(self):
		class NotWorkflowBuilder:
			pass

		instance = NotWorkflowBuilder()
		self.assertFalse(_in_workflow_execution(instance))

	def test_task_decorator_direct_call(self):
		class TestDoc(WorkflowBuilder):
			@task
			def my_task(self):
				return "task result"

		instance = TestDoc({"doctype": "Press Workflow Test"})
		result = instance.my_task()
		self.assertEqual(result, "task result")

	def test_task_decorator_with_queue_and_timeout(self):
		class TestDoc(WorkflowBuilder):
			@task(queue="long", timeout=3600)
			def my_task(self):
				return "task result"

		instance = TestDoc({"doctype": "Press Workflow Test"})
		result = instance.my_task()
		self.assertEqual(result, "task result")

	def test_task_with_task_id(self):
		class TestDoc(WorkflowBuilder):
			@task
			def my_task(self, task_id=None):
				return f"task_id={task_id}"

		instance = TestDoc({"doctype": "Press Workflow Test"})
		result = instance.my_task.with_task_id("my-id")()
		self.assertEqual(result, "task_id=my-id")

	def test_task_with_task_id_in_workflow(self):
		wf_name = self.doc.main_with_task_id_passthrough.run_as_workflow()
		wf = frappe.get_doc("Press Workflow", wf_name)
		wf.run()

		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 9)

	def test_flow_decorator_normal_call(self):
		result = self.doc.main_success()
		self.assertEqual(result, "success output")

	def test_flow_decorator_run_as_workflow(self):
		wf_name = self.doc.main_success.run_as_workflow()
		self.assertTrue(wf_name)
		self.assertTrue(frappe.db.exists("Press Workflow", wf_name))

	def test_flow_decorator_with_args(self):
		wf_name = self.doc.flow_with_args.run_as_workflow(x=5, y=10)
		wf = frappe.get_doc("Press Workflow", wf_name)
		wf.run()

		self.assertEqual(wf.status, "Success")
		self.assertEqual(wf.get_result(), 15)

	def test_flow_descriptor_on_non_document_raises(self):
		with self.assertRaises((TypeError, RuntimeError)):

			class NotADocument:
				@flow
				def my_flow(self):
					pass

	def test_run_as_workflow_on_non_workflow_builder_raises(self):
		class TestDoc(Document):
			@flow
			def my_flow(self):
				return "result"

		instance = TestDoc({"doctype": "Press Workflow Test"})
		instance.name = "test"
		instance.doctype = "TestDoc"

		bound_flow = instance.my_flow
		self.assertIsInstance(bound_flow, BoundFlow)

		with self.assertRaises(TypeError):
			bound_flow.run_as_workflow()

	def test_flow_callable_protocol(self):
		bound_flow = self.doc.main_success
		self.assertTrue(callable(bound_flow))
		self.assertTrue(hasattr(bound_flow, "run_as_workflow"))

	def test_task_descriptor_class_access(self):
		class TestDoc(WorkflowBuilder):
			@task
			def my_task(self):
				return "result"

		self.assertTrue(hasattr(TestDoc, "my_task"))

	def test_task_without_task_id_strips_kwarg(self):
		class TestDoc(WorkflowBuilder):
			@task
			def my_task(self):
				return "no task_id"

		instance = TestDoc({"doctype": "Press Workflow Test"})
		result = instance.my_task()
		self.assertEqual(result, "no task_id")

	def test_flow_creates_workflow_with_steps(self):
		wf_name = self.doc.main_with_task.run_as_workflow()
		wf = frappe.get_doc("Press Workflow", wf_name)

		self.assertEqual(wf.linked_doctype, "Press Workflow Test")
		self.assertEqual(wf.linked_docname, self.doc.name)
		self.assertEqual(wf.main_method_name, "main_with_task")
		self.assertTrue(len(wf.steps) > 0)
