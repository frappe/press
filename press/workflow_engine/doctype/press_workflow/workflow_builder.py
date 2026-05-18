# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal, TypeVar

import frappe
from frappe.model.document import Document

from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow_kv.press_workflow_kv import (
	InMemoryKVStore,
	KVStoreInterface,
	WorkflowKVStore,
)
from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
	ObjectDeserializeError,
	ObjectPreviousSerializationFailedError,
)
from press.workflow_engine.utils import (
	deserialize_value,
	generate_function_signature,
	is_func_accept_task_id,
	method_title,
	serialize_and_store_value,
)

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.press_workflow import PressWorkflow
	from press.workflow_engine.doctype.press_workflow_task.press_workflow_task import (
		PressWorkflowTask,
	)


F1 = TypeVar("F1", bound=Callable[..., Any])


def ensure_to_resolve_context(fn: F1) -> F1:
	@wraps(fn)
	def wrapper(self: "WorkflowBuilder", *args, **kwargs):
		self.resolve_context()
		return fn(self, *args, **kwargs)

	return wrapper  # type: ignore


class WorkflowBuilder(Document):
	workflow_name: str | None = None
	_workflow_doc_cache: "PressWorkflow | None" = None
	kv_store_type: Literal["in_memory", "workflow_store"] = "in_memory"
	kv_store_reference: KVStoreInterface | None = None
	current_task_signature: str | None = None

	@property
	def workflow_doc(self) -> "PressWorkflow | None":
		if self._workflow_doc_cache is None and self.workflow_name:
			self._workflow_doc_cache = frappe.get_doc("Press Workflow", self.workflow_name)  # type: ignore
		return self._workflow_doc_cache

	@workflow_doc.setter
	def workflow_doc(self, value: "PressWorkflow | None") -> None:
		self._workflow_doc_cache = value

	@ensure_to_resolve_context
	def run_task(  # noqa: C901
		self,
		wrapped: Callable[..., object],
		args: tuple,
		kwargs: dict,
		queue: str | None = None,
		timeout: int | None = None,
	) -> Any:
		assert self.workflow_name is not None, "Workflow name must be set to enqueue task"

		signature = generate_function_signature(wrapped, args, kwargs)
		if self.current_task_signature and self.current_task_signature == signature:
			new_kwargs = kwargs.copy()
			if not is_func_accept_task_id(wrapped):
				new_kwargs.pop("task_id", None)

			return wrapped(self, *args, **new_kwargs)

		task_name: str | None = frappe.db.exists(
			"Press Workflow Task",
			{
				"workflow": self.workflow_name,
				"signature": signature,
			},
		)  # type: ignore

		if not task_name:
			task_doc: PressWorkflowTask = frappe.new_doc("Press Workflow Task")  # type: ignore
			task_doc.workflow = self.workflow_name  # type: ignore
			task_doc.method_name = wrapped.__name__  # type: ignore

			task_doc.method_title = method_title(wrapped)  # type: ignore

			task_doc.signature = signature  # type: ignore
			args_type, args_value = serialize_and_store_value(args)
			kwargs_type, kwargs_value = serialize_and_store_value(kwargs)
			task_doc.args = args_value
			task_doc.args_type = args_type
			task_doc.kwargs = kwargs_value
			task_doc.kwargs_type = kwargs_type
			task_doc.status = "Queued"  # type: ignore
			task_doc.queue = queue  # type: ignore
			task_doc.timeout = timeout or 0  # type: ignore

			# If we are currently inside a running task, record it as the parent
			# so the new task can re-enqueue it when it completes.
			task_doc.parent_task = getattr(self.flags, "current_press_workflow_task", None)  # type: ignore
			task_doc.insert(ignore_permissions=True)

			# If workflow want to monitor this step
			# Store the reference of the task in workflow doctype
			# If it's a nested task, ignore it
			if not task_doc.parent_task and (
				tracked_step := frappe.db.exists(
					"Press Workflow Step",
					{
						"parenttype": "Press Workflow",
						"parent": self.workflow_name,
						"step_method": wrapped.__name__,
						"task": ("is", "not set"),
					},
				)
			):
				frappe.db.set_value("Press Workflow Step", str(tracked_step), "task", task_doc.name)

			task_name = task_doc.name
			assert task_name, "Task must be saved successfully before it can be run"

		status = frappe.db.get_value("Press Workflow Task", task_name, "status")
		if status in ["Queued", "Running"]:
			raise PressWorkflowTaskEnqueued(
				f"Task {task_name} is in {status} state",
				self.workflow_name,
				task_name,
			)

		task_doc: PressWorkflowTask = frappe.get_doc("Press Workflow Task", task_name)  # type: ignore
		if task_doc.status == "Success":
			return deserialize_value(task_doc.output_type, task_doc.output)

		if task_doc.status == "Failure":
			if task_doc.exception:
				try:
					exc = deserialize_value("object", task_doc.exception)
				except ObjectPreviousSerializationFailedError as e:
					raise RuntimeError(
						f"Task '{task_doc.method_title}' failed. Original exception could not be "
						f"deserialized. Summary: {e.summary}"
					) from e
				except ObjectDeserializeError as e:
					raise RuntimeError(
						f"Task '{task_doc.method_title}' failed and its exception could not be deserialized: {e}"
					) from e
				if isinstance(exc, BaseException):
					raise exc
				raise RuntimeError(
					f"Task '{task_doc.method_title}' failed with a non-exception object: {exc!r}"
				)
			raise RuntimeError(f"Task '{task_doc.method_title}' failed with no recorded exception.")

		raise Exception(f"Task {task_doc.method_title} is in an unknown state: {task_doc.status}")

	@property
	@ensure_to_resolve_context
	def kv(self) -> KVStoreInterface:
		if self.kv_store_reference:
			return self.kv_store_reference

		if self.kv_store_type == "in_memory":
			# Fallback for calls outside of workflow context
			self.kv_store_reference = InMemoryKVStore()

		elif self.kv_store_type == "workflow_store":
			assert self.workflow_name is not None, (
				"Workflow name must be set in frappe.flags.current_workflow to use workflow_store KV store."
			)

			self.kv_store_reference = WorkflowKVStore(self.workflow_name)

		else:
			raise ValueError(f"Invalid KV store type: {self.kv_store_type}")

		return self.kv_store_reference

	def resolve_context(self) -> None:
		if self.workflow_name or self.workflow_doc:
			return

		current_workflow = getattr(frappe.flags, "current_press_workflow", None)
		if current_workflow:
			self.workflow_name = str(current_workflow)
			# workflow_doc will be loaded lazily on first access
			if self.kv_store_type != "workflow_store":
				# Store type is changing — discard any cached in-memory store.
				self.kv_store_type = "workflow_store"
				self.kv_store_reference = None
		else:
			if self.kv_store_type != "in_memory":
				self.kv_store_type = "in_memory"
				self.kv_store_reference = None

	def defer_current_task(self, message: str = "User has requested to defer the task later.") -> None:
		if not self.flags.in_press_workflow_execution:
			return

		assert self.workflow_name is not None, "Workflow name must be set to defer current task"

		raise PressWorkflowTaskEnqueued(
			message,
			self.workflow_name,
			self.flags.current_press_workflow_task
			if hasattr(self.flags, "current_press_workflow_task")
			else None,
		)
