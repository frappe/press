"""Utility methods for writing tests"""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from collections.abc import Callable


def foreground_enqueue_doc(
	doctype: str,
	docname: str,
	method: str,
	queue="default",
	timeout=None,
	now=False,  # default args unused to avoid them from going to kwargs
	enqueue_after_commit=False,
	job_id=None,
	deduplicate=False,
	at_front: bool = False,
	**kwargs,
):
	"""
	Run enqueued method in foreground

	Use for monkey patching enqueue_doc in tests
	"""
	getattr(frappe.get_doc(doctype, docname), method)(**kwargs)


def foreground_enqueue(
	method: str | Callable,
	queue: str = "default",
	timeout: int | None = None,
	event=None,
	is_async: bool = True,
	job_name: str | None = None,
	now: bool = True,
	enqueue_after_commit: bool = False,
	*,
	on_success: Callable | None = None,
	on_failure: Callable | None = None,
	at_front: bool = False,
	job_id: str | None = None,
	deduplicate: bool = False,
	**kwargs,
):
	return frappe.call(method, **kwargs)
