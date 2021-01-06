# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
import pprint

import frappe
from frappe.model.document import Document


class RemoteOperationLog(Document):
	pass


def make_log(operation_type, status="Success"):
	"""Make log after remote operation."""

	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			req = args[-1]
			res = func(*args, **kwargs)
			frappe.get_doc(
				doctype="Remote Operation Log",
				operation_type=operation_type,
				request=pprint.pformat(req),
				response=pprint.pformat(res),
				status=status,
			).insert()

			return res

		return wrapper

	return decorator
