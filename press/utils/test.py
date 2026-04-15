"""Utility methods for writing tests"""

import sys
from collections.abc import Callable
from urllib.parse import urlparse, urlunparse

import frappe
import requests


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


def _foreground_run_workflow_doc(doctype: str, docname: str, job_id: str) -> None:
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

	if job_id in in_flight:
		# Already executing this job - defer until the outermost call drains it.
		print(
			f"[FG] DEFER  {job_id} (in-flight: {sorted(in_flight)})",
			file=sys.stderr,
			flush=True,
		)
		pending[job_id] = (doctype, docname)
		return

	print(f"[FG] START  {job_id}", file=sys.stderr, flush=True)
	in_flight.add(job_id)
	method_title = "unknown_method"
	try:
		doc = frappe.get_doc(doctype, docname)
		method_title = (
			doc.main_method_title
			if hasattr(doc, "main_method_title")
			else (doc.method_title if hasattr(doc, "method_title") else "unknown_method")
		)
		print(
			f"[FG] RUN    {job_id} {method_title} | status={getattr(doc, 'status', '?')}",
			file=sys.stderr,
			flush=True,
		)
		doc.run()
		print(
			f"[FG] DONE   {job_id} {method_title} | status={getattr(frappe.get_doc(doctype, docname), 'status', '?')}",
			file=sys.stderr,
			flush=True,
		)
		# Drain any re-enqueue requests that arrived while this job was running.
		retry = 0
		while job_id in pending:
			retry += 1
			pending.pop(job_id)
			print(f"[FG] RETRY  {job_id} {method_title} (#{retry})", file=sys.stderr, flush=True)
			doc = frappe.get_doc(doctype, docname)
			print(
				f"[FG] RUN    {job_id} {method_title} | status={getattr(doc, 'status', '?')} (retry #{retry})",
				file=sys.stderr,
				flush=True,
			)
			doc.run()
			print(
				f"[FG] DONE   {job_id} {method_title} | status={getattr(frappe.get_doc(doctype, docname), 'status', '?')} (retry #{retry})",
				file=sys.stderr,
				flush=True,
			)
	finally:
		print(
			f"[FG] FINISH {job_id} {method_title} | pending={list(pending.keys())}",
			file=sys.stderr,
			flush=True,
		)
		in_flight.discard(job_id)


def foreground_enqueue_task(task_name: str) -> None:
	print(f"[FG] enqueue_task({task_name})", file=sys.stderr, flush=True)
	_foreground_run_workflow_doc(
		"Press Workflow Task",
		task_name,
		f"press_workflow_task||{task_name}||run",
	)


def foreground_enqueue_workflow(workflow_name: str) -> None:
	print(f"[FG] enqueue_workflow({workflow_name})", file=sys.stderr, flush=True)
	_foreground_run_workflow_doc(
		"Press Workflow",
		workflow_name,
		f"press_workflow||{workflow_name}||run",
	)


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
