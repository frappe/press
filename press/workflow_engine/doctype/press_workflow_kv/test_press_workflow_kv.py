# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.workflow_engine.doctype.press_workflow_kv.press_workflow_kv import (
	InMemoryKVStore,
	WorkflowKVStore,
)


class TestPressWorkflowKV(FrappeTestCase):
	def setUp(self):
		self.workflow_name = frappe.generate_hash(length=10)
		self.store = WorkflowKVStore(workflow_name=self.workflow_name)

	def tearDown(self):
		frappe.db.delete("Press Workflow KV", {"parent": self.workflow_name})
		frappe.db.delete("Press Workflow Object")

	def test_in_memory_kv_store(self):
		store = InMemoryKVStore()
		store.set("test_key", "test_value")
		self.assertEqual(store.get("test_key"), "test_value")

		store.delete("test_key")
		self.assertIsNone(store.get("test_key"))

	def test_workflow_kv_store_set_and_get(self):
		self.store.set("test_key", {"data": 123})

		value = self.store.get("test_key")
		self.assertEqual(value, {"data": 123})

	def test_workflow_kv_store_update(self):
		self.store.set("test_key", "initial_value")
		initial_kv_name = self.store._get_kv_record_name("test_key")
		initial_type, initial_value = frappe.db.get_value(
			"Press Workflow KV", initial_kv_name, ["type", "value"]
		)

		self.store.set("test_key", "updated_value")
		updated_kv_name = self.store._get_kv_record_name("test_key")
		_, updated_value = frappe.db.get_value("Press Workflow KV", updated_kv_name, ["type", "value"])

		self.assertEqual(initial_kv_name, updated_kv_name)
		self.assertNotEqual(initial_value, updated_value)

		# For JSON-serializable values, no Press Workflow Object is created.
		# Only verify object deletion tracking when type is "object".
		if initial_type == "object":
			is_deleted = frappe.db.get_value("Press Workflow Object", initial_value, "deleted")
			self.assertTrue(is_deleted)

		value = self.store.get("test_key")
		self.assertEqual(value, "updated_value")

	def test_workflow_kv_store_delete(self):
		self.store.set("test_key", "to_be_deleted")
		kv_name = self.store._get_kv_record_name("test_key")
		obj_type, obj_name = frappe.db.get_value("Press Workflow KV", kv_name, ["type", "value"])

		self.store.delete("test_key")

		self.assertFalse(frappe.db.exists("Press Workflow KV", kv_name))

		# Only Press Workflow Object documents are marked as deleted.
		# JSON-serializable values are stored directly in the KV record.
		if obj_type == "object":
			is_deleted = frappe.db.get_value("Press Workflow Object", obj_name, "deleted")
			self.assertTrue(is_deleted)

		self.assertIsNone(self.store.get("test_key"))

	def test_workflow_kv_store_get_nonexistent(self):
		self.assertIsNone(self.store.get("nonexistent_key"))

	def test_in_memory_kv_store_multiple_keys(self):
		store = InMemoryKVStore()
		store.set("key1", "value1")
		store.set("key2", "value2")
		store.set("key3", "value3")

		self.assertEqual(store.get("key1"), "value1")
		self.assertEqual(store.get("key2"), "value2")
		self.assertEqual(store.get("key3"), "value3")

	def test_in_memory_kv_store_overwrite(self):
		store = InMemoryKVStore()
		store.set("key", "initial")
		store.set("key", "updated")

		self.assertEqual(store.get("key"), "updated")

	def test_in_memory_kv_store_delete_nonexistent(self):
		store = InMemoryKVStore()
		store.delete("nonexistent")
		self.assertIsNone(store.get("nonexistent"))

	def test_workflow_kv_store_with_none_value(self):
		self.store.set("null_key", None)
		self.assertIsNone(self.store.get("null_key"))

	def test_workflow_kv_store_with_complex_value(self):
		value = {"nested": {"data": [1, 2, 3]}, "list": ["a", "b", "c"]}
		self.store.set("complex_key", value)
		retrieved = self.store.get("complex_key")
		self.assertEqual(retrieved, value)

	def test_workflow_kv_store_multiple_keys(self):
		self.store.set("key1", "value1")
		self.store.set("key2", "value2")

		self.assertEqual(self.store.get("key1"), "value1")
		self.assertEqual(self.store.get("key2"), "value2")

	def test_workflow_kv_store_delete_nonexistent(self):
		self.store.delete("nonexistent_key")
		self.assertIsNone(self.store.get("nonexistent_key"))
