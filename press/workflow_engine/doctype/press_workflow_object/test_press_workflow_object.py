# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
	ObjectPreviousSerializationFailedError,
	ObjectSerializeError,
	PressWorkflowObject,
)

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class MyCustomClass:
	def __init__(self, name: str, value: int):
		self.name = name
		self.value = value

	def __eq__(self, other):
		if not isinstance(other, MyCustomClass):
			return False
		return self.name == other.name and self.value == other.value


class IntegrationTestPressWorkflowObject(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_store_and_get_success(self):
		obj = {"key": "value", "list": [1, 2, 3], "nested": {"a": "b"}}
		doc_name = PressWorkflowObject.store(obj)

		self.assertTrue(doc_name)
		retrieved = PressWorkflowObject.get_object(doc_name)
		self.assertEqual(retrieved, obj)

	def test_store_and_get_custom_class(self):
		obj = MyCustomClass("test_name", 42)
		doc_name = PressWorkflowObject.store(obj)

		self.assertTrue(doc_name)
		retrieved = PressWorkflowObject.get_object(doc_name)
		self.assertIsInstance(retrieved, MyCustomClass)
		self.assertEqual(retrieved, obj)
		self.assertEqual(retrieved.name, "test_name")
		self.assertEqual(retrieved.value, 42)

	def test_store_serialization_error_throw(self):
		# Lambdas cannot be pickled
		with self.assertRaises(ObjectSerializeError):
			PressWorkflowObject.store(lambda x: x, throw_on_error=True)

	def test_store_serialization_error_no_throw(self):
		doc_name = PressWorkflowObject.store(lambda x: x, throw_on_error=False)

		# Should store successfully but flag as failed
		self.assertTrue(doc_name)

		summary = PressWorkflowObject.get_summary(doc_name)
		self.assertIsInstance(summary, str)

		# Getting the object should raise the previous failure exception
		with self.assertRaises(ObjectPreviousSerializationFailedError) as context:
			PressWorkflowObject.get_object(doc_name)

		self.assertIn("Serialization previously failed", str(context.exception))
		self.assertEqual(context.exception.summary, summary)

	def test_get_summary(self):
		obj = [1, 2, 3, "test"]
		doc_name = PressWorkflowObject.store(obj)

		summary = PressWorkflowObject.get_summary(doc_name)
		self.assertEqual(summary, str(obj))

	def test_get_summary_nonexistent(self):
		with self.assertRaises(frappe.DoesNotExistError):
			PressWorkflowObject.get_summary("nonexistent-doc-name")

	def test_get_object_nonexistent(self):
		with self.assertRaises(frappe.DoesNotExistError):
			PressWorkflowObject.get_object("nonexistent-doc-name")

	def test_store_and_get_none_value(self):
		doc_name = PressWorkflowObject.store(None)
		self.assertTrue(doc_name)
		retrieved = PressWorkflowObject.get_object(doc_name)
		self.assertIsNone(retrieved)

	def test_store_and_get_complex_nested_object(self):
		obj = {
			"list_of_dicts": [{"a": 1}, {"b": 2}],
			"dict_of_lists": {"x": [1, 2], "y": [3, 4]},
			"nested": {"deep": {"deeper": {"value": 42}}},
		}
		doc_name = PressWorkflowObject.store(obj)
		retrieved = PressWorkflowObject.get_object(doc_name)
		self.assertEqual(retrieved, obj)

	def test_delete_trashed_objects(self):
		from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
			delete_trashed_objects,
		)

		obj = {"key": "value"}
		doc_name = PressWorkflowObject.store(obj)

		frappe.db.set_value("Press Workflow Object", doc_name, "deleted", True)

		delete_trashed_objects()

		self.assertFalse(frappe.db.exists("Press Workflow Object", doc_name))
