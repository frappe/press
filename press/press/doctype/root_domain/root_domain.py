# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.utils import log_error


class RootDomain(Document):
	def after_insert(self):
		if not frappe.db.exists("TLS Certificate", {"wildcard": True, "domain": self.name}):
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"obtain_root_domain_tls_certificate",
				enqueue_after_commit=True,
			)

	def obtain_root_domain_tls_certificate(self):
		try:
			rsa_key_size = frappe.db.get_value(
				"Press Settings", "Press Settings", "rsa_key_size"
			)
			frappe.get_doc(
				{
					"doctype": "TLS Certificate",
					"wildcard": True,
					"domain": self.name,
					"rsa_key_size": rsa_key_size,
				}
			).insert()
		except Exception:
			log_error("Root Domain TLS Certificate Exception")
