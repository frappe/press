# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
import pprint

import frappe
from frappe.model.document import Document


class RemoteOperationLog(Document):
	@classmethod
	def make_log(cls, operation_type: str, status: str = "Unknown"):
		"""
		Make log after remote operation.

		Takes first arg of decorated method as bucket name.
		Takes second arg of decorated method as request.
		"""

		def decorator(func):
			@functools.wraps(func)
			def wrapper(*args, **kwargs):
				try:
					bucket = args[0]
				except IndexError:
					raise "Bucket name not given"
				try:
					req = args[1]
				except IndexError:
					req = None
				res = func(*args, **kwargs)
				frappe.get_doc(
					doctype="Remote Operation Log",
					operation_type=operation_type,
					request=pprint.pformat(req),
					response=pprint.pformat(res),
					status=status,
					bucket=bucket,
				).insert()

				return res

			return wrapper

		return decorator
