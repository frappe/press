# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import ast
import dataclasses
import hashlib
import inspect
import json
import math
import textwrap
from collections.abc import Callable
from datetime import datetime
from typing import Any

from frappe.model.document import Document
from frappe.utils import get_datetime


def method_title(func: Callable[..., Any]) -> str:
	if func.__doc__:
		return func.__doc__.strip().split("\n")[0]
	return func.__name__.replace("_", " ").title()


class SelfCallVisitor(ast.NodeVisitor):
	def __init__(self, cls: type) -> None:
		self.cls = cls
		self.calls: list[tuple[str, str]] = []
		self._own_methods: frozenset[str] = frozenset(cls.__dict__)

	def visit_Call(self, node: ast.Call) -> None:
		func = node.func
		if (
			isinstance(func, ast.Attribute)
			and isinstance(func.value, ast.Name)
			and func.value.id == "self"
			and func.attr in self._own_methods
		):
			self.calls.append((func.attr, method_title(getattr(self.cls, func.attr))))
		self.generic_visit(node)


def called_methods_in_order(cls: type, func_or_name: str | Callable[..., Any]) -> list[tuple[str, str]]:
	func = func_or_name if callable(func_or_name) else inspect.unwrap(getattr(cls, func_or_name))
	source = textwrap.dedent(inspect.getsource(func))
	visitor = SelfCallVisitor(cls)
	visitor.visit(ast.parse(source))
	return visitor.calls


def calculate_duration(start: str | datetime, end: str | datetime) -> int:
	start_dt = get_datetime(start)
	end_dt = get_datetime(end)
	assert start_dt is not None and end_dt is not None
	return int((end_dt - start_dt).total_seconds())


def _canonicalize(obj: Any, visited: set | None = None) -> Any:  # noqa: C901 - some crazy internal use better to not touch?
	if visited is None:
		visited = set()

	if obj is None or isinstance(obj, bool | int | str):
		return obj

	if isinstance(obj, float):
		if math.isnan(obj):
			return "__NaN__"
		if obj == float("inf"):
			return "__Inf__"
		if obj == float("-inf"):
			return "__-Inf__"
		return obj

	obj_id = id(obj)
	if obj_id in visited:
		raise ValueError(f"Circular reference detected in object of type {type(obj).__qualname__!r}")

	visited.add(obj_id)

	try:
		if isinstance(obj, list | tuple):
			return {
				"__type__": type(obj).__name__,
				"values": [_canonicalize(x, visited) for x in obj],
			}

		if isinstance(obj, dict):
			return {
				"__type__": "dict",
				"values": {
					str(k): _canonicalize(v, visited) for k, v in sorted(obj.items(), key=lambda x: str(x[0]))
				},
			}

		if isinstance(obj, set | frozenset):
			canonicalized = [_canonicalize(x, visited) for x in obj]
			sorted_values = sorted(canonicalized, key=lambda x: json.dumps(x, sort_keys=True))
			return {"__type__": type(obj).__name__, "values": sorted_values}

		if isinstance(obj, Document):
			return {
				"__type__": obj.doctype,
				"doctype": obj.doctype,
				"name": obj.name,
			}

		if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
			return {
				"__type__": f"{type(obj).__module__}.{type(obj).__qualname__}",
				"fields": _canonicalize(dataclasses.asdict(obj), visited),
			}

		try:
			import numpy as np

			if isinstance(obj, np.ndarray):
				return {
					"__type__": "ndarray",
					"dtype": str(obj.dtype),
					"shape": list(obj.shape),
					"data": obj.flatten().tolist(),
				}
		except ImportError:
			pass

		raise TypeError(
			f"Cannot canonicalize type {type(obj).__qualname__!r}. "
			f"Convert to a supported type or extend _canonicalize before calling generate_signature."
		)

	finally:
		visited.discard(obj_id)


def is_func_accept_task_id(func: Callable) -> bool:
	"""Return True if `func` has an explicit `task_id` parameter."""
	sig = inspect.signature(func)
	return "task_id" in sig.parameters


def generate_function_signature(func: Callable, args: tuple, kwargs: dict) -> str:
	kwargs = kwargs.copy()
	task_id = kwargs.pop("task_id", None)

	sig = inspect.signature(func)
	# Drop `self` - args never includes the instance (it's the unbound function)
	params = list(sig.parameters.values())
	if params and params[0].name == "self":
		sig = sig.replace(parameters=params[1:])
	bound = sig.bind(*args, **kwargs)
	bound.apply_defaults()

	payload = {
		"func": {
			"module": func.__module__,
			"qualname": func.__qualname__,
		},
		"arguments": _canonicalize(dict(bound.arguments)),
	}

	if task_id is not None:
		payload["task_id"] = task_id

	blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
	return hashlib.sha256(blob).hexdigest()
