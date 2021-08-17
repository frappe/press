# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from functools import cached_property

import boto3
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

	@cached_property
	def boto3_client(self):
		return boto3.client(
			"route53",
			aws_access_key_id=self.aws_access_key_id,
			aws_secret_access_key=self.get_password("aws_secret_access_key"),
		)

	@property
	def hosted_zone(self):
		return self.boto3_client.list_hosted_zones_by_name(DNSName=self.name)[
			"HostedZones"
		][0]["Id"]
