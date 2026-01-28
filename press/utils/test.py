"""Utility methods for writing tests"""

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
