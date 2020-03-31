# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.utils import log_error


class PressSettings(Document):
	def obtain_root_domain_tls_certificate(self):
		frappe.enqueue_doc(self.doctype, self.name, "_obtain_root_domain_tls_certificate")

	def _obtain_root_domain_tls_certificate(self):
		try:
			certificate = frappe.get_doc(
				{
					"doctype": "TLS Certificate",
					"wildcard": True,
					"domain": self.domain,
					"rsa_key_size": self.rsa_key_size,
				}
			).insert()
			self.wildcard_tls_certificate = certificate.name
			self.save()
		except Exception:
			log_error("Root Domain TLS Exception")
