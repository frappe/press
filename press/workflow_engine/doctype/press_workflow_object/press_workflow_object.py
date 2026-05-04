# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import pickle
from typing import Any

import frappe
from frappe.model.document import Document


class ObjectSerializeError(frappe.ValidationError):
	"""Raised when an object cannot be serialized into a Press Workflow Object."""

	pass


class ObjectDeserializeError(frappe.ValidationError):
	"""Raised when a Press Workflow Object cannot be deserialized."""

	pass


class ObjectPreviousSerializationFailedError(ObjectDeserializeError):
	"""Raised when deserialization fails because the original serialization failed.
	The stored object summary is accessible via the `summary` attribute.
	"""

	def __init__(self, message: str, summary: str = ""):
		super().__init__(message)
		self.summary = summary


class PressWorkflowObject(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		deleted: DF.Check
		serialization_failed: DF.Check
		serialized: DF.LongText | None
		summary: DF.Data
		type_qualname: DF.Data
	# end: auto-generated types

	@staticmethod
	def store(obj: Any, throw_on_error: bool = True) -> str:
		"""
		Serialize and store any Python object.

		Args:
			obj: The Python object to serialize.
			throw_on_error: If True, raises `PressWorkflowObjectSerializeError` on failure.
							If False, stores a summary of the object and flags it as failed.

		Returns:
			str: The name of the created `Press Workflow Object` document.

		Raises:
			ObjectSerializeError: If pickling fails and `throw_on_error` is True.
		"""
		type_qualname = f"{type(obj).__module__}.{type(obj).__qualname__}"
		if len(type_qualname) > 256:
			type_qualname = type_qualname[:250] + "..."

		doc: PressWorkflowObject = frappe.new_doc("Press Workflow Object")  # type: ignore
		doc.type_qualname = type_qualname
		doc.serialization_failed = False

		try:
			summary = str(obj)
		except Exception:
			summary = repr(type(obj))

		if not summary:
			summary = f"Instance of {type_qualname}"

		if len(summary) > 512:
			summary = summary[:500] + "..."
		doc.summary = summary

		try:
			doc.serialized = base64.b64encode(pickle.dumps(obj)).decode("ascii")
		except Exception as exc:
			if throw_on_error:
				raise ObjectSerializeError(
					f"Failed to serialize object of type {type_qualname!r}: {exc}"
				) from exc

			doc.serialized = None
			doc.serialization_failed = True

		doc.insert(ignore_permissions=True)
		return str(doc.name)

	@staticmethod
	def get_object(doc_name: str) -> Any:
		"""
		Retrieves and deserializes a stored Python object by its document name.

		Args:
			doc_name: The name of the `Press Workflow Object` document.

		Returns:
			Any: The deserialized Python object.

		Raises:
			ObjectPreviousSerializationFailedError: If the object originally failed to serialize.
				The object's stored summary is accessible via the exception's `summary` attribute.
			ObjectDeserializeError: If the document exists but deserialization fails.
		"""
		doc: PressWorkflowObject = frappe.get_doc("Press Workflow Object", doc_name)  # type: ignore

		if doc.serialization_failed:
			raise ObjectPreviousSerializationFailedError(
				f"Cannot deserialize {doc_name!r}: Serialization previously failed for object of type {doc.type_qualname!r}.",
				summary=doc.summary,
			)

		if not doc.serialized:
			raise ObjectDeserializeError(f"Object of type {doc.type_qualname!r} has no serialized data.")

		try:
			return pickle.loads(base64.b64decode(doc.serialized.encode("ascii")))
		except Exception as exc:
			raise ObjectDeserializeError(
				f"Failed to deserialize object of type {doc.type_qualname!r}: {exc}"
			) from exc

	@staticmethod
	def get_summary(doc_name: str) -> str:
		"""
		Fetch only the summary of a stored object without deserializing it.
		Useful for logging, debugging, or re-raising exceptions efficiently.

		Args:
			doc_name: The name of the `Press Workflow Object` document.

		Returns:
			str: A string summary of the object.

		Raises:
			frappe.DoesNotExistError: If the document doesn't exist.
		"""
		summary = frappe.db.get_value("Press Workflow Object", doc_name, "summary")

		if summary is None:
			frappe.throw(
				f"Press Workflow Object {doc_name!r} does not exist.",
				exc=frappe.DoesNotExistError,
			)

		return str(summary)


def delete_trashed_objects():
	frappe.db.delete("Press Workflow Object", {"deleted": 1})
