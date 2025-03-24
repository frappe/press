# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Iterable

import boto3
import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.utils import log_error


class RootDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		aws_access_key_id: DF.Data | None
		aws_secret_access_key: DF.Password | None
		default_cluster: DF.Link
		dns_provider: DF.Literal["AWS Route 53", "Generic"]
		team: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		if self.dns_provider != "Generic" and not frappe.db.exists(
			"TLS Certificate", {"wildcard": True, "domain": self.name}
		):
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"obtain_root_domain_tls_certificate",
				enqueue_after_commit=True,
			)

	def obtain_root_domain_tls_certificate(self):
		try:
			rsa_key_size = frappe.db.get_value("Press Settings", "Press Settings", "rsa_key_size")
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
	def generic_dns_provider(self):
		if not hasattr(self, "_generic_dns_provider"):
			self._generic_dns_provider = self.dns_provider == "Generic"

		return self._generic_dns_provider

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

	def delete_dns_records(self, records: list[str]):
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
			["request_data", "server"],
		)
		server_map = {server.name: server.cluster for server in frappe.get_all("Server", ["name", "cluster"])}
		return {json.loads(site.request_data)["new_name"]: server_map[site.server] for site in renaming_sites}

	def get_active_site_domains(self):
		Domain = frappe.qb.DocType("Site Domain")
		Site = frappe.qb.DocType("Site")
		query = (
			frappe.qb.from_(Domain)
			.left_join(Site)
			.on(Domain.site == Site.name)
			.where(Domain.domain.like(f"%{self.name}%"))
			.where(Domain.status == "Active")
			.select(Domain.domain, Site.cluster)
		)
		return {domain.domain: domain.cluster for domain in query.run(as_dict=True)}

	def get_active_domains(self):
		active_sites = frappe.get_all(
			"Site", {"status": ("!=", "Archived"), "domain": self.name}, ["name", "cluster"]
		)
		active_domains = {site.name: site.cluster for site in active_sites}
		active_domains.update(self.get_sites_being_renamed())
		active_domains.update(self.get_active_site_domains())
		return active_domains

	def get_default_cluster_proxies(self):
		proxy_map = {}
		domains = frappe.get_all("Root Domain", ["name", "default_cluster"])
		for domain in domains:
			proxies = frappe.get_all(
				"Proxy Server", {"status": "Active", "cluster": domain.default_cluster}, pluck="name"
			)
			proxy_map[domain.name] = proxies[0]
		return proxy_map

	def remove_unused_cname_records(self):
		proxies = frappe.get_all("Proxy Server", {"status": "Active"}, pluck="name")

		default_proxies = self.get_default_cluster_proxies()

		for page in self.get_dns_record_pages():
			to_delete = []

			frappe.db.commit()
			active_domains = self.get_active_domains()

			for record in page["ResourceRecordSets"]:
				# Only look at CNAME records that point to a proxy server
				if record["Type"] == "CNAME" and record["ResourceRecords"][0]["Value"] in proxies:
					domain = record["Name"].strip(".")
					# Delete inactive records
					if domain not in active_domains:
						record["Name"] = domain
						to_delete.append(record)
					# Delete records that point to a proxy in the default_cluster
					# These are covered by * records
					elif record["ResourceRecords"][0]["Value"] in default_proxies.get(
						active_domains[domain], []
					):
						to_delete.append(record)
			if to_delete:
				self.delete_dns_records(to_delete)

	def update_dns_records_for_sites(self, sites: list[str], proxy_server: str):
		if self.generic_dns_provider:
			return

		# update records in batches of 500
		batch_size = 500
		for i in range(0, len(sites), batch_size):
			changes = []
			for site in sites[i : i + batch_size]:
				changes.append(
					{
						"Action": "UPSERT",
						"ResourceRecordSet": {
							"Name": site,
							"Type": "CNAME",
							"TTL": 600,
							"ResourceRecords": [{"Value": proxy_server}],
						},
					}
				)

			self.boto3_client.change_resource_record_sets(
				ChangeBatch={"Changes": changes}, HostedZoneId=self.hosted_zone
			)


def cleanup_cname_records():
	domains = frappe.get_all("Root Domain", pluck="name")
	for domain_name in domains:
		domain = RootDomain("Root Domain", domain_name)
		if domain.generic_dns_provider:
			continue

		domain.remove_unused_cname_records()
