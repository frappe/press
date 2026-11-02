# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations


class PressWorkflowTaskEnqueued(Exception):
	"""Raised when a task is enqueued and the flow needs to be paused."""

	def __init__(self, message: str, workflow_name: str, task_name: str | None = None):
		super().__init__(message)
		self.workflow_name = workflow_name
		self.task_name = task_name


class PressWorkflowRunningError(Exception):
	"""Raised when trying to get result of a running or queued workflow."""

	pass


class PressWorkflowFailedError(Exception):
	"""Raised when the workflow failed but no exception was recorded."""

	pass


class PressWorkflowFatalError(Exception):
	"""Raised when the workflow encountered a fatal error."""

	def __init__(self, message: str, traceback: str | None = None):
		super().__init__(message)
		self.traceback = traceback
