"""Utility methods for writing tests"""

import os
import sys
from collections.abc import Callable
from urllib.parse import urlparse, urlunparse

import frappe
import requests

_workflow_log_buffer: list[str] = []


def foreground_enqueue_doc_with_user(run_as_user: str):
	def wrapper(*args, **kwargs):
		# Remove any user-supplied run_as_user
		kwargs.pop("run_as_user", None)

		current_user = frappe.session.user
		if run_as_user:
			frappe.set_user(run_as_user)

		try:
			return foreground_enqueue_doc(*args, **kwargs)
		finally:
			frappe.set_user(current_user)

	return wrapper


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


def _foreground_run_workflow_doc(doctype: str, docname: str, job_id: str, max_retries: int = 50) -> None:  # noqa: C901
	"""
	Tracks in-flight job IDs to prevent direct recursion. When the same job_id
	is re-enqueued while it is already on the call-stack the request is deferred;
	once the outermost invocation finishes, deferred calls are drained in order.
	This mirrors the enqueue_after_commit + deduplication semantics used in
	production.
	"""
	if not hasattr(frappe.local, "_fg_wf_in_flight"):
		frappe.local._fg_wf_in_flight = set()
	if not hasattr(frappe.local, "_fg_wf_pending"):
		frappe.local._fg_wf_pending = {}

	in_flight: set = frappe.local._fg_wf_in_flight
	pending: dict = frappe.local._fg_wf_pending

	log_immediate = os.environ.get("PRESS_LOG_WORKFLOW_DEBUG_INFO") in ("1", "true", "True")

	def _log(msg: str) -> None:
		_workflow_log_buffer.append(msg)
		if log_immediate:
			print(msg, file=sys.stderr, flush=True)

	if job_id in in_flight:
		# Already executing this job - defer until the outermost call drains it.
		_log(f"[WORKFLOW] DEFER  {job_id} (in-flight: {sorted(in_flight)})")
		pending[job_id] = (doctype, docname)
		return

	_log(f"[WORKFLOW] START  {job_id}")

	in_flight.add(job_id)
	method_title = "unknown_method"
	try:
		doc = frappe.get_doc(doctype, docname)
		method_title = (
			doc.main_method_title
			if hasattr(doc, "main_method_title")
			else (doc.method_title if hasattr(doc, "method_title") else "unknown_method")
		)
		_log(f"[WORKFLOW] RUN    {job_id} {method_title} | status={getattr(doc, 'status', '?')}")
		doc.run()
		_log(
			f"[WORKFLOW] DONE   {job_id} {method_title} | status={getattr(frappe.get_doc(doctype, docname), 'status', '?')}"
		)
		# Drain any re-enqueue requests that arrived while this job was running.
		retry = 0
		while job_id in pending:
			retry += 1
			if retry > max_retries:
				_log(
					f"[WORKFLOW] MAX RETRIES EXCEEDED for {job_id} {method_title} | pending={list(pending.keys())}"
				)
				break
			pending.pop(job_id)
			_log(f"[WORKFLOW] RETRY  {job_id} {method_title} (#{retry})")
			doc = frappe.get_doc(doctype, docname)
			_log(
				f"[WORKFLOW] RUN    {job_id} {method_title} | status={getattr(doc, 'status', '?')} (retry #{retry})"
			)
			doc.run()
			_log(
				f"[WORKFLOW] DONE   {job_id} {method_title} | status={getattr(frappe.get_doc(doctype, docname), 'status', '?')} (retry #{retry})"
			)
	except Exception:
		raise
	finally:
		_log(f"[WORKFLOW] FINISH {job_id} {method_title} | pending={list(pending.keys())}")
		in_flight.discard(job_id)


def foreground_enqueue_task(task_name: str) -> None:
	_foreground_run_workflow_doc(
		"Press Workflow Task",
		task_name,
		f"press_workflow_task||{task_name}||run",
	)


def foreground_enqueue_workflow(workflow_name: str) -> None:
	log_immediate = os.environ.get("PRESS_LOG_WORKFLOW_DEBUG_INFO") in ("1", "true", "True")
	_workflow_log_buffer.clear()
	_foreground_run_workflow_doc(
		"Press Workflow",
		workflow_name,
		f"press_workflow||{workflow_name}||run",
	)
	if not log_immediate:
		doc = frappe.get_doc("Press Workflow", workflow_name)
		if getattr(doc, "status", None) == "Failure":
			for msg in _workflow_log_buffer:
				print(msg, file=sys.stderr, flush=True)


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


def request_locally_with_host_rewrite(deletion_url: str, **kwargs) -> requests.Response:
	parsed = urlparse(deletion_url)
	original_host = parsed.hostname
	port = parsed.port or (443 if parsed.scheme == "https" else 80)

	if original_host not in ("localhost", "127.0.0.1"):
		new_netloc = f"127.0.0.1:{port}"
		rewritten_url = urlunparse(parsed._replace(netloc=new_netloc))
		headers = kwargs.pop("headers", {})
		headers["Host"] = original_host
	else:
		rewritten_url = deletion_url
		headers = kwargs.pop("headers", {})

	return requests.get(rewritten_url, headers=headers, **kwargs)
