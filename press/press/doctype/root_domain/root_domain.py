# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


from datetime import datetime, timedelta
import json
from typing import Iterable, List

import boto3
import frappe
from frappe.model.document import Document
from frappe.core.utils import find

from press.utils import log_error


class RootDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		aws_access_key_id: DF.Data
		aws_secret_access_key: DF.Password
		default_cluster: DF.Link
		dns_provider: DF.Literal["AWS Route 53"]
	# end: auto-generated types

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

	@property
	def boto3_client(self):
		if not hasattr(self, "_boto3_client"):
			self._boto3_client = boto3.client(
				"route53",
				aws_access_key_id=self.aws_access_key_id,
				aws_secret_access_key=self.get_password("aws_secret_access_key"),
			)
		return self._boto3_client

	@property
	def hosted_zone(self):
		zones = self.boto3_client.list_hosted_zones_by_name()["HostedZones"]
		return find(reversed(zones), lambda x: self.name.endswith(x["Name"][:-1]))["Id"]

	def get_dns_record_pages(self) -> Iterable:
		try:
			paginator = self.boto3_client.get_paginator("list_resource_record_sets")
			return paginator.paginate(
				PaginationConfig={"MaxItems": 10000, "PageSize": 300, "StartingToken": "0"},
				HostedZoneId=self.hosted_zone.split("/")[-1],
			)
		except Exception:
			log_error("Route 53 Pagination Error", domain=self.name)

	def delete_dns_records(self, records: List[str]):
		try:
			changes = []
			for record in records:
				changes.append({"Action": "DELETE", "ResourceRecordSet": record})

			self.boto3_client.change_resource_record_sets(
				ChangeBatch={"Changes": changes}, HostedZoneId=self.hosted_zone
			)

		except Exception:
			log_error("Route 53 Record Deletion Error", domain=self.name)

	def get_sites_being_renamed(self):
		# get sites renamed in Server but doc not renamed in press
		last_hour = datetime.now() - timedelta(hours=1)  # very large bound just to be safe
		renaming_sites = frappe.get_all(
			"Agent Job",
			{"job_type": "Rename Site", "creation": (">=", last_hour)},
			pluck="request_data",
		)
		return [json.loads(d_str)["new_name"] for d_str in renaming_sites]

	def get_active_domains(self):
		active_sites = frappe.get_all(
			"Site", {"status": ("!=", "Archived"), "domain": self.name}, pluck="name"
		)
		active_sites.extend(self.get_sites_being_renamed())
		return active_sites

	def remove_unused_cname_records(self):
		proxies = frappe.get_all("Proxy Server", {"status": "Active"}, pluck="name")
		for page in self.get_dns_record_pages():
			to_delete = []

			frappe.db.commit()
			active = self.get_active_domains()

			for record in page["ResourceRecordSets"]:
				if record["Type"] == "CNAME" and record["ResourceRecords"][0]["Value"] in proxies:
					domain = record["Name"].strip(".")
					if domain not in active:
						record["Name"] = domain
						to_delete.append(record)
			if to_delete:
				self.delete_dns_records(to_delete)


def cleanup_cname_records():
	domains = frappe.get_all("Root Domain", pluck="name")
	for domain_name in domains:
		domain = frappe.get_doc("Root Domain", domain_name)
		domain.remove_unused_cname_records()
