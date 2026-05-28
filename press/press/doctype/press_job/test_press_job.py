# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for press_job/press_job.py.

arguments_dict() is a pure JSON-parsing method.
virtual_machine_doc property returns None when no VM is linked.
Both are tested without DB round-trips.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_job.press_job import PressJob

_MODULE = "press.press.doctype.press_job.press_job"


def _job(arguments=None, virtual_machine=None, server_type="Server", server="srv-1"):
	"""Return a SimpleNamespace mimicking a PressJob document."""
	doc = SimpleNamespace(
		arguments=json.dumps(arguments) if arguments is not None else None,
		virtual_machine=virtual_machine,
		server_type=server_type,
		server=server,
	)
	# Mimic Frappe Document.get()
	doc.get = lambda field, default=None: getattr(doc, field, default)
	return doc


class TestPressJobArgumentsDict(FrappeTestCase):
	"""arguments_dict() parses JSON arguments into a frappe._dict."""

	def test_returns_dict_from_valid_json(self):
		doc = _job(arguments={"site": "mysite.com", "action": "backup"})
		result = PressJob.arguments_dict.fget(doc)
		self.assertEqual(result["site"], "mysite.com")
		self.assertEqual(result["action"], "backup")

	def test_returns_empty_dict_when_arguments_is_none(self):
		doc = _job(arguments=None)
		result = PressJob.arguments_dict.fget(doc)
		self.assertEqual(result, {})

	def test_returns_empty_dict_when_arguments_is_empty_string(self):
		doc = _job()
		doc.arguments = ""
		result = PressJob.arguments_dict.fget(doc)
		self.assertEqual(result, {})

	def test_returns_frappe_dict(self):
		doc = _job(arguments={"key": "val"})
		result = PressJob.arguments_dict.fget(doc)
		self.assertIsInstance(result, frappe._dict)

	def test_nested_arguments_preserved(self):
		doc = _job(arguments={"config": {"debug": True, "level": 3}})
		result = PressJob.arguments_dict.fget(doc)
		self.assertEqual(result["config"]["debug"], True)


class TestPressJobVirtualMachineDoc(FrappeTestCase):
	"""virtual_machine_doc property returns None when virtual_machine is not set."""

	def test_returns_none_when_no_virtual_machine(self):
		doc = _job(virtual_machine=None)
		result = PressJob.virtual_machine_doc.fget(doc)
		self.assertIsNone(result)

	def test_fetches_doc_when_virtual_machine_is_set(self):
		doc = _job(virtual_machine="vm-1")
		vm_mock = object()
		with patch(f"{_MODULE}.frappe.get_doc", return_value=vm_mock):
			result = PressJob.virtual_machine_doc.fget(doc)
		self.assertIs(result, vm_mock)
