# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import dataclasses
from datetime import datetime, timedelta

from frappe.tests.utils import FrappeTestCase

from press.workflow_engine.utils import (
	_canonicalize,
	calculate_duration,
	called_methods_in_order,
	deserialize_value,
	generate_function_signature,
	get_type_of_value,
	is_func_accept_task_id,
	method_title,
	serialize_and_store_value,
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

	def test_serialize_deserialize_json_types(self):
		cases = [
			(True, "bool"),
			(7, "int"),
			(1.5, "float"),
			("value", "string"),
			((1, "a"), "tuple"),
			([1, "a"], "list"),
			({"a": 1}, "dict"),
		]

		for original, expected_type in cases:
			with self.subTest(value=original, value_type=expected_type):
				value_type, serialized_value = serialize_and_store_value(original)
				self.assertEqual(value_type, expected_type)
				deserialized_value = deserialize_value(value_type, serialized_value)
				self.assertEqual(type(deserialized_value), type(original))
				self.assertEqual(deserialized_value, original)

	def test_serialize_deserialize_exception_as_object(self):
		original = ValueError("something went wrong")
		value_type, serialized_value = serialize_and_store_value(original)

		self.assertEqual(value_type, "object")
		self.assertIsNotNone(serialized_value)

		deserialized = deserialize_value(value_type, serialized_value)
		self.assertIsInstance(deserialized, ValueError)
		self.assertEqual(str(deserialized), str(original))

	def test_get_type_of_value_none(self):
		self.assertIsNone(get_type_of_value(None))

	def test_get_type_of_value_bool(self):
		self.assertEqual(get_type_of_value(True), "bool")
		self.assertEqual(get_type_of_value(False), "bool")

	def test_get_type_of_value_int(self):
		self.assertEqual(get_type_of_value(0), "int")
		self.assertEqual(get_type_of_value(-100), "int")
		self.assertEqual(get_type_of_value(999999), "int")

	def test_get_type_of_value_float_finite(self):
		self.assertEqual(get_type_of_value(1.5), "float")
		self.assertEqual(get_type_of_value(0.0), "float")

	def test_get_type_of_value_float_infinite(self):
		self.assertEqual(get_type_of_value(float("inf")), "object")
		self.assertEqual(get_type_of_value(float("-inf")), "object")
		self.assertEqual(get_type_of_value(float("nan")), "object")

	def test_get_type_of_value_string(self):
		self.assertEqual(get_type_of_value(""), "string")
		self.assertEqual(get_type_of_value("hello"), "string")

	def test_get_type_of_value_tuple_serializable(self):
		self.assertEqual(get_type_of_value((1, 2, 3)), "tuple")
		self.assertEqual(get_type_of_value(("a", "b")), "tuple")

	def test_get_type_of_value_tuple_non_serializable(self):
		self.assertEqual(get_type_of_value((float("inf"),)), "object")

	def test_get_type_of_value_list_serializable(self):
		self.assertEqual(get_type_of_value([1, 2, 3]), "list")

	def test_get_type_of_value_list_non_serializable(self):
		self.assertEqual(get_type_of_value([float("inf")]), "object")

	def test_get_type_of_value_dict_serializable(self):
		self.assertEqual(get_type_of_value({"a": 1, "b": 2}), "dict")

	def test_get_type_of_value_dict_non_serializable(self):
		self.assertEqual(get_type_of_value({"a": float("inf")}), "object")

	def test_get_type_of_value_custom_object(self):
		obj = DummyDataclass(a=1, b="test")
		self.assertEqual(get_type_of_value(obj), "object")

	def test_serialize_and_store_value_none(self):
		value_type, serialized_value = serialize_and_store_value(None)
		self.assertIsNone(value_type)
		self.assertIsNone(serialized_value)

	def test_serialize_and_store_value_object(self):
		obj = DummyDataclass(a=1, b="test")
		value_type, serialized_value = serialize_and_store_value(obj)
		self.assertEqual(value_type, "object")
		self.assertIsNotNone(serialized_value)

	def test_deserialize_value_none_type(self):
		self.assertIsNone(deserialize_value(None, None))

	def test_deserialize_value_invalid_json(self):
		with self.assertRaises(ValueError):
			deserialize_value("dict", "not valid json")

	def test_deserialize_value_unsupported_type(self):
		with self.assertRaises(ValueError):
			deserialize_value("unsupported", "value")

	def test_canonicalize_frozenset(self):
		result = _canonicalize(frozenset([1, 2, 3]))
		self.assertEqual(result["__type__"], "frozenset")
		self.assertEqual(sorted(result["values"]), [1, 2, 3])

	def test_generate_function_signature_with_self(self):
		class MyClass:
			def my_method(self, a, b):
				pass

		sig = generate_function_signature(MyClass.my_method, args=(1, 2), kwargs={})
		self.assertIsInstance(sig, str)
		self.assertTrue(len(sig) > 0)

	def test_generate_function_signature_different_args(self):
		def my_func(a, b):
			pass

		sig1 = generate_function_signature(my_func, args=(1, 2), kwargs={})
		sig2 = generate_function_signature(my_func, args=(3, 4), kwargs={})
		self.assertNotEqual(sig1, sig2)

	def test_is_func_accept_task_id_with_kwargs(self):
		def func_with_kwargs(**kwargs):
			pass

		self.assertFalse(is_func_accept_task_id(func_with_kwargs))

	def test_is_func_accept_task_id_with_variadic(self):
		def func_with_variadic(*args, **kwargs):
			pass

		self.assertFalse(is_func_accept_task_id(func_with_variadic))

	def test_method_title_with_multiline_docstring(self):
		def func():
			"""First line
			Second line
			Third line
			"""
			pass

		self.assertEqual(method_title(func), "First line")

	def test_method_title_with_underscores(self):
		def my_function_name():
			pass

		self.assertEqual(method_title(my_function_name), "My Function Name")

	def test_called_methods_in_order_with_method_name(self):
		calls = called_methods_in_order(DummyClassForCallVisitor, "method_three")
		self.assertEqual(len(calls), 2)
		self.assertEqual(calls[0][0], "method_one")
		self.assertEqual(calls[1][0], "method_two")

	def test_serialize_deserialize_empty_collections(self):
		cases = [
			([], "list"),
			((), "tuple"),
			({}, "dict"),
		]

		for original, expected_type in cases:
			with self.subTest(value=original, value_type=expected_type):
				value_type, serialized_value = serialize_and_store_value(original)
				self.assertEqual(value_type, expected_type)
				deserialized_value = deserialize_value(value_type, serialized_value)
				self.assertEqual(deserialized_value, original)
