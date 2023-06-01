""" Utility methods for writing tests """

import frappe


def foreground_enqueue_doc(
	doctype: str,
	docname: str,
	doc_method: str,
	queue="default",
	timeout=None,
	now=False,  # default args unused to avoid them from going to kwargs
	**kwargs
):
	"""
	Run enqueued method in foreground

	Use for monkey patching enqueue_doc in tests
	"""
	getattr(frappe.get_doc(doctype, docname), doc_method)(**kwargs)
