# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import dataclasses
from datetime import datetime, timedelta

from frappe.tests.utils import FrappeTestCase

from press.workflow_engine.utils import (
	_canonicalize,
	calculate_duration,
	called_methods_in_order,
	generate_function_signature,
	is_func_accept_task_id,
	method_title,
)


@dataclasses.dataclass
class DummyDataclass:
	a: int
	b: str


class DummyClassForCallVisitor:
	def method_one(self):
		pass

	def method_two(self):
		"""Custom Title For Two"""
		pass

	def method_three(self):
		self.method_one()
		self.method_two()


class TestWorkflowEngineUtils(FrappeTestCase):
	def test_method_title(self):
		# fmt: off
		def func_with_doc():
			"""This is a Docstring
			Second Line
			"""
			pass
		# fmt: on

		def func_without_doc():
			pass

		self.assertEqual(method_title(func_with_doc), "This is a Docstring")
		self.assertEqual(method_title(func_without_doc), "Func Without Doc")

	def test_called_methods_in_order(self):
		calls = called_methods_in_order(DummyClassForCallVisitor, "method_three")
		expected = [
			("method_one", "Method One"),
			("method_two", "Custom Title For Two"),
		]
		self.assertEqual(calls, expected)

	def test_calculate_duration(self):
		start = datetime(2026, 1, 1, 12, 0, 0)
		end = start + timedelta(seconds=150)

		# Test with datetime objects
		self.assertEqual(calculate_duration(start, end), 150)

		# Test with string objects
		self.assertEqual(calculate_duration(str(start), str(end)), 150)

	def test_canonicalize_basic_types(self):
		self.assertIsNone(_canonicalize(None))
		self.assertEqual(_canonicalize(1), 1)
		self.assertEqual(_canonicalize("test"), "test")
		self.assertEqual(_canonicalize(True), True)

	def test_canonicalize_floats(self):
		self.assertEqual(_canonicalize(1.5), 1.5)
		self.assertEqual(_canonicalize(float("inf")), "__Inf__")
		self.assertEqual(_canonicalize(float("-inf")), "__-Inf__")
		self.assertEqual(_canonicalize(float("nan")), "__NaN__")

	def test_canonicalize_collections(self):
		# List
		self.assertEqual(
			_canonicalize([1, "a", None]),
			{"__type__": "list", "values": [1, "a", None]},
		)

		# Tuple
		self.assertEqual(
			_canonicalize((1, 2)),
			{"__type__": "tuple", "values": [1, 2]},
		)

		# Dict
		self.assertEqual(
			_canonicalize({"b": 2, "a": 1}),
			{"__type__": "dict", "values": {"a": 1, "b": 2}},
		)

		# Set
		self.assertEqual(
			_canonicalize({2, 1}),
			{"__type__": "set", "values": [1, 2]},  # Sorted
		)

	def test_canonicalize_dataclass(self):
		obj = DummyDataclass(a=1, b="2")
		result = _canonicalize(obj)

		self.assertEqual(result["__type__"], f"{__name__}.DummyDataclass")
		self.assertEqual(result["fields"], {"__type__": "dict", "values": {"a": 1, "b": "2"}})

	def test_canonicalize_circular_reference(self):
		circular_list = []
		circular_list.append(circular_list)
		with self.assertRaisesRegex(ValueError, "Circular reference detected"):
			_canonicalize(circular_list)

	def test_is_func_accept_task_id(self):
		def func_with_task_id(a, b, task_id):
			pass

		def func_without_task_id(a, b):
			pass

		self.assertTrue(is_func_accept_task_id(func_with_task_id))
		self.assertFalse(is_func_accept_task_id(func_without_task_id))

	def test_generate_function_signature(self):
		def my_func(a, b=2, task_id=None):
			pass

		sig1 = generate_function_signature(my_func, args=(1,), kwargs={})
		sig2 = generate_function_signature(my_func, args=(1,), kwargs={"b": 2})
		sig3 = generate_function_signature(my_func, args=(1, 2), kwargs={})

		self.assertEqual(sig1, sig2)
		self.assertEqual(sig1, sig3)

		# task_id should be ignored in the signature arguments, but included in payload.
		sig4 = generate_function_signature(my_func, args=(1,), kwargs={"task_id": "123"})
		# In this implementation, the payload structure incorporates task_id so the digest will be different.
		self.assertNotEqual(sig1, sig4)
