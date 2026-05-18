# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import abc
from typing import Any

import frappe
from frappe.model.document import Document

from press.workflow_engine.utils import deserialize_value, serialize_and_store_value


class KVStoreInterface(abc.ABC):
	@abc.abstractmethod
	def set(self, key: str, value: Any, throw_on_error: bool = True):
		pass

	@abc.abstractmethod
	def get(self, key: str) -> Any | None:
		pass

	@abc.abstractmethod
	def delete(self, key: str):
		pass


class WorkflowKVStore(KVStoreInterface):
	def __init__(self, workflow_name: str) -> None:
		self.workflow_name = workflow_name
		self.parent_field = "key_value_store"
		self.parent_type = "Press Workflow"

	def set(self, key: str, value: Any, throw_on_error: bool = True):
		kv_name = self._get_kv_record_name(key)
		if kv_name:
			kv_doc: PressWorkflowKV = frappe.get_doc("Press Workflow KV", kv_name)  # type: ignore
		else:
			kv_doc = frappe.new_doc("Press Workflow KV")  # type: ignore
			kv_doc.parent = self.workflow_name
			kv_doc.parentfield = self.parent_field
			kv_doc.parenttype = self.parent_type
			kv_doc.key = key

		if kv_doc.value and kv_doc.type == "object":
			frappe.db.set_value("Press Workflow Object", str(kv_doc.value), "deleted", True)

		value_type, value = serialize_and_store_value(value, throw_on_error=throw_on_error)
		if value_type is None:
			self.delete(key)
			return

		kv_doc.type = value_type
		kv_doc.value = value
		kv_doc.save(ignore_permissions=True)

	def get(self, key: str) -> Any | None:
		kv_name = self._get_kv_record_name(key)
		if not kv_name:
			return None

		value, value_type = frappe.db.get_value("Press Workflow KV", kv_name, ["value", "type"])
		if not value:
			return None

		return deserialize_value(value_type, value)

	def delete(self, key: str):
		kv_name = self._get_kv_record_name(key)
		if kv_name:
			object_name = frappe.db.get_value("Press Workflow KV", kv_name, "value")
			if object_name:
				frappe.db.set_value("Press Workflow Object", str(object_name), "deleted", True)
			frappe.delete_doc("Press Workflow KV", kv_name, force=True)

	def _get_kv_record_name(self, key: str) -> str | None:
		name = frappe.db.exists(
			"Press Workflow KV",
			{
				"parent": self.workflow_name,
				"parentfield": self.parent_field,
				"parenttype": self.parent_type,
				"key": key,
			},
		)
		if name:
			return str(name)
		return None


class InMemoryKVStore(KVStoreInterface):
	def __init__(self):
		self.store = {}

	def set(self, key: str, value: Any, throw_on_error: bool = True):
		self.store[key] = value

	def get(self, key: str) -> Any | None:
		return self.store.get(key)

	def delete(self, key: str):
		if key in self.store:
			del self.store[key]


class PressWorkflowKV(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		key: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Literal["int", "float", "string", "tuple", "list", "dict", "object"]
		value: DF.Data | None
	# end: auto-generated types
