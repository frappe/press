# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import inspect
import typing
from functools import wraps
from typing import Any, Concatenate, Generic, ParamSpec, Protocol, TypeVar, overload

import frappe
from frappe.model.document import Document

from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder
from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
	PressWorkflowObject,
)
from press.workflow_engine.utils import (
	called_methods_in_order,
	is_func_accept_task_id,
	method_title,
)

if typing.TYPE_CHECKING:
	from collections.abc import Callable
	from inspect import Signature


def _in_workflow_execution(instance: WorkflowBuilder | None) -> bool:
	return bool(
		isinstance(instance, WorkflowBuilder)
		and getattr(instance, "name", None)
		and getattr(instance, "workflow_name", None)
		and getattr(instance.flags, "in_press_workflow_execution", False)
	)


_P = ParamSpec("_P")
_R = TypeVar("_R")
_R_co = TypeVar("_R_co", covariant=True)


class _BoundTask(Generic[_P, _R_co]):
	def __init__(self, wrapped: Callable[..., _R_co], instance: WorkflowBuilder) -> None:
		self._wrapped = wrapped
		self._instance = instance
		self._task_id: str | None = None
		wraps(wrapped)(self)

	def _execute(self, args: tuple, kwargs: dict) -> _R_co:
		if self._task_id is not None:
			kwargs = {**kwargs, "task_id": self._task_id}

		if _in_workflow_execution(self._instance):
			return self._instance.run_task(self._wrapped, args, kwargs)  # type: ignore[return-value]

		if not is_func_accept_task_id(self._wrapped):
			kwargs = {k: v for k, v in kwargs.items() if k != "task_id"}
		return self._wrapped(self._instance, *args, **kwargs)

	def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R_co:
		return self._execute(args, kwargs)  # type: ignore[arg-type]

	def with_task_id(self, task_id: str) -> "_BoundTask[_P, _R_co]":
		bound: _BoundTask[_P, _R_co] = _BoundTask(self._wrapped, self._instance)
		bound._task_id = task_id
		return bound  # type: ignore[return-value]


class _TaskDescriptor(Generic[_P, _R_co]):
	def __init__(self, wrapped: Callable[Concatenate[Any, _P], _R_co]) -> None:
		self._wrapped = wrapped
		wraps(wrapped)(self)  # type: ignore[arg-type]

	def __set_name__(self, owner: type, name: str) -> None:
		self._name = name

	@overload
	def __get__(self, instance: None, owner: type) -> "_TaskDescriptor[_P, _R_co]": ...

	@overload
	def __get__(self, instance: Any, owner: type) -> _BoundTask[_P, _R_co]: ...

	def __get__(self, instance: Any, owner: type) -> Any:
		if instance is None:
			return self
		return _BoundTask(self._wrapped, instance)


def task(wrapped: Callable[Concatenate[Any, _P], _R]) -> _TaskDescriptor[_P, _R]:
	"""Mark a method as a workflow task.

	When called inside an active workflow execution, the method is handed off
	to the workflow engine (enqueued, tracked, retried). Outside a workflow
	it behaves like a normal method call. Supports `.with_task_id()` to
	attach an explicit task identifier.
	"""
	return _TaskDescriptor(wrapped)


_Self = TypeVar("_Self")


class FlowCallable(Protocol[_P, _R_co]):
	def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R_co: ...
	def run_as_workflow(self, *args: _P.args, **kwargs: _P.kwargs) -> str: ...


class BoundFlow:
	def __init__(self, instance: Any, signature_without_self: Signature, wrapped: Callable) -> None:
		self._instance = instance
		self._wrapped = wrapped
		self._signature_without_self = signature_without_self

	def __call__(self, *args: Any, **kwargs: Any) -> Any:
		return self._wrapped(self._instance, *args, **kwargs)

	def run_as_workflow(self, *args: Any, **kwargs: Any) -> str:
		self._signature_without_self.bind(*args, **kwargs)

		instance = self._instance
		if not isinstance(instance, WorkflowBuilder):
			raise TypeError(
				"run_as_workflow() can only be called on instances of WorkflowBuilder subclasses."
			)

		methods = called_methods_in_order(type(instance), self._wrapped)

		seen: set[str] = set()
		methods = [m for m in methods if not (m[0] in seen or seen.add(m[0]))]  # type: ignore[func-returns-value]

		return (
			frappe.get_doc(
				{
					"doctype": "Press Workflow",
					"args": PressWorkflowObject.store(args) if args else None,
					"kwargs": PressWorkflowObject.store(kwargs) if kwargs else None,
					"linked_doctype": instance.doctype,  # type: ignore
					"linked_docname": instance.name,  # type: ignore
					"main_method_name": self._wrapped.__name__,
					"main_method_title": method_title(self._wrapped),
					"steps": [
						{
							"step_title": title,
							"step_method": name,
							"status": "Pending",
						}
						for name, title in methods
					],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)


@overload
def flow(wrapped: Callable[Concatenate[_Self, _P], _R_co]) -> FlowCallable[_P, _R_co]: ...


@overload
def flow(wrapped: Callable[..., Any]) -> Any: ...


def flow(wrapped: Callable[..., Any]) -> Any:
	"""Mark a method as a workflow flow.

	Direct calls execute the method normally. Calling `.run_as_workflow()`
	instead creates a Press Workflow document, auto-discovers the `self.*`
	task calls via AST inspection, and registers them as tracked steps.
	"""
	sig = inspect.signature(wrapped)
	params = list(sig.parameters.values())
	sig_without_self = sig.replace(parameters=params[1:] if params and params[0].name == "self" else params)

	class FlowDescriptor:
		def __set_name__(self, owner: type, name: str) -> None:
			if not issubclass(owner, Document):
				raise TypeError(
					f"@flow can only decorate methods on Document subclasses. "
					f"'{owner.__name__}' does not inherit from Document."
				)

		def __get__(self, instance: Any, owner: type) -> Any:
			if instance is None:
				return self
			return BoundFlow(instance=instance, signature_without_self=sig_without_self, wrapped=wrapped)

	return FlowDescriptor()
