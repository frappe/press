# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from press.workflow_engine.doctype.press_workflow.exceptions import (
	PressWorkflowFailedError,
	PressWorkflowFatalError,
	PressWorkflowRunningError,
	PressWorkflowTaskEnqueued,
)


class TestPressWorkflowExceptions(FrappeTestCase):
	def test_press_workflow_task_enqueued_with_task_name(self):
		exc = PressWorkflowTaskEnqueued("Task is enqueued", "wf-001", "task-001")
		self.assertEqual(str(exc), "Task is enqueued")
		self.assertEqual(exc.workflow_name, "wf-001")
		self.assertEqual(exc.task_name, "task-001")

	def test_press_workflow_task_enqueued_without_task_name(self):
		exc = PressWorkflowTaskEnqueued("Task is enqueued", "wf-001")
		self.assertEqual(str(exc), "Task is enqueued")
		self.assertEqual(exc.workflow_name, "wf-001")
		self.assertIsNone(exc.task_name)

	def test_press_workflow_running_error(self):
		exc = PressWorkflowRunningError("Workflow wf-001 is currently running")
		self.assertEqual(str(exc), "Workflow wf-001 is currently running")

	def test_press_workflow_failed_error(self):
		exc = PressWorkflowFailedError("Workflow failed with no exception")
		self.assertEqual(str(exc), "Workflow failed with no exception")

	def test_press_workflow_fatal_error_with_traceback(self):
		traceback = "Traceback (most recent call last):\n  File 'test.py', line 1"
		exc = PressWorkflowFatalError("Fatal error occurred", traceback=traceback)
		self.assertEqual(str(exc), "Fatal error occurred")
		self.assertEqual(exc.traceback, traceback)

	def test_press_workflow_fatal_error_without_traceback(self):
		exc = PressWorkflowFatalError("Fatal error occurred")
		self.assertEqual(str(exc), "Fatal error occurred")
		self.assertIsNone(exc.traceback)

	def test_exceptions_are_subclasses_of_exception(self):
		self.assertTrue(issubclass(PressWorkflowTaskEnqueued, Exception))
		self.assertTrue(issubclass(PressWorkflowRunningError, Exception))
		self.assertTrue(issubclass(PressWorkflowFailedError, Exception))
		self.assertTrue(issubclass(PressWorkflowFatalError, Exception))

	def test_catch_press_workflow_task_enqueued(self):
		with self.assertRaises(PressWorkflowTaskEnqueued) as ctx:
			raise PressWorkflowTaskEnqueued("Test message", "wf-001", "task-001")
		self.assertEqual(ctx.exception.workflow_name, "wf-001")
		self.assertEqual(ctx.exception.task_name, "task-001")

	def test_catch_press_workflow_fatal_error(self):
		with self.assertRaises(PressWorkflowFatalError) as ctx:
			raise PressWorkflowFatalError("Test fatal", traceback="test traceback")
		self.assertEqual(ctx.exception.traceback, "test traceback")
