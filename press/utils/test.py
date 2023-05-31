""" Utility methods for writing tests """

import frappe


def foreground_enqueue_doc(
	doctype: str,
	docname: str,
	doc_method: str,
	queue="default",  # default arg unused to avoid going to kwargs
	timeout=None,
	now=False,
	**kwargs
):
	"""
	Run enqueued method in foreground

	Use for monkey patching enqueue_doc in tests
	"""
	getattr(frappe.get_doc(doctype, docname), doc_method)(**kwargs)
