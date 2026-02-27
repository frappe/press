# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import boto3
from cloudflare import Cloudflare
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils.caching import redis_cache

from press.utils import log_error

if TYPE_CHECKING:
	from collections.abc import Iterable

	from press.press.doctype.proxy_server.proxy_server import ProxyServer


class RootDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		aws_access_key_id: DF.Data | None
		aws_region: DF.Data | None
		aws_secret_access_key: DF.Password | None
		cloud_flare_api_key: DF.Password | None
		default_cluster: DF.Link
		default_proxy_server: DF.Link | None
		dns_provider: DF.Literal["AWS Route 53", "Cloud Flare", "Generic"]
		enabled: DF.Check
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
					"provider": "Let's Encrypt",
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
				region_name=self.aws_region,
			)
		return self._boto3_client

	@property
	def cloudflare_client(self):
		if not hasattr(self, "_cloudflare_client"):
			self._cloudflare_client = Cloudflare(
				token=self.get_password("cloud_flare_api_key")
			)

		return self._cloudflare_client

	@property
	def cloudflare_zone_id(self):
		# Cloudflare zones API returns a list, we must search
		zones = self.cloudflare_client.zones.get(params={"name": self.name})
		if zones:
			return zones[0]["id"]
		return frappe.throw(f"Cloudflare Zone not found for {self.name}")

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
		return []

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
			pluck="request_data",
		)
		return [json.loads(d_str)["new_name"] for d_str in renaming_sites]

	def get_active_site_domains(self):
		return frappe.get_all(
			"Site Domain", {"domain": ("like", f"%{self.name}"), "status": "Active"}, pluck="name"
		)

	def get_active_sites(self):
		return frappe.get_all("Site", {"status": ("!=", "Archived"), "domain": self.name}, pluck="name")

	def get_active_domains(self):
		active_domains = self.get_active_sites()
		active_domains.extend(self.get_sites_being_renamed())
		active_domains.extend(self.get_active_site_domains())
		return set(active_domains)

	def get_default_cluster_proxies(self):
		return frappe.get_all(
			"Proxy Server", {"status": "Active", "cluster": self.default_cluster}, pluck="name"
		)

	def remove_unused_cname_records(self):
		proxies = frappe.get_all("Proxy Server", {"status": "Active"}, pluck="name")

		default_proxies = self.get_default_cluster_proxies()

		for page in self.get_dns_record_pages():
			to_delete = []

			frappe.db.commit()
			active_domains = self.get_active_domains()

			for record in page["ResourceRecordSets"]:
				# Only look at CNAME records that point to a proxy server
				value = record["ResourceRecords"][0]["Value"]
				if record["Type"] == "CNAME" and value in proxies:
					domain = record["Name"].strip(".")
					# Delete inactive records
					if domain not in active_domains:  # noqa: SIM114
						record["Name"] = domain
						to_delete.append(record)
					# Delete records that point to a proxy in the default_cluster
					# These are covered by * records
					elif value in default_proxies:
						record["Name"] = domain
						to_delete.append(record)
			if to_delete:
				self.delete_dns_records(to_delete)

	def update_dns_records_for_sites(
		self, sites: list[str], proxy_server: str, batch_size: int = 500, ttl: int = 600
	):
		if self.generic_dns_provider:
			return

		# update records in batches
		for i in range(0, len(sites), batch_size):
			changes = []
			for site in sites[i : i + batch_size]:
				changes.append(
					{
						"Action": "UPSERT",
						"ResourceRecordSet": {
							"Name": site,
							"Type": "CNAME",
							"TTL": ttl,
							"ResourceRecords": [{"Value": proxy_server}],
						},
					}
				)

			self.boto3_client.change_resource_record_sets(
				ChangeBatch={"Changes": changes}, HostedZoneId=self.hosted_zone
			)

	@frappe.whitelist()
	def add_to_proxies(self):
		proxies = frappe.get_all("Proxy Server", {"status": "Active"}, pluck="name")
		for proxy_name in proxies:
			proxy: ProxyServer = frappe.get_doc("Proxy Server", proxy_name)
			proxy.append("domains", {"domain": self.name})
			proxy.save()
			proxy.setup_wildcard_hosts()


def cleanup_cname_records():
	domains = frappe.get_all("Root Domain", pluck="name")
	for domain_name in domains:
		domain = RootDomain("Root Domain", domain_name)
		if domain.generic_dns_provider:
			continue

		domain.remove_unused_cname_records()


@redis_cache(ttl=3600)
def get_domains():
	return frappe.get_all("Root Domain", filters={"enabled": ["=", "1"]}, pluck="name")


def get_matching_domain(domain: str) -> str | None:
	root_domains = get_domains()
	for rd in root_domains:
		if domain == rd or domain.endswith(f".{rd}"):
			return rd
	return None
