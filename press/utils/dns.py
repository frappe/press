from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
import frappe
from frappe.core.utils import find

from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.root_domain.root_domain import RootDomain


@frappe.whitelist()
def create_dns_record(doc, record_name=None):
	"""Check if site needs dns records and creates one."""
	domain = frappe.get_doc("Root Domain", doc.domain)

	if domain.generic_dns_provider:
		return

	if frappe.flags.in_test:
		return

	proxy_server, is_standalone = frappe.get_value("Server", doc.server, ["proxy_server", "is_standalone"])

	if doc.cluster == domain.default_cluster and not is_standalone:
		# Check if the cluster has multiple proxy servers
		proxy_servers = frappe.get_all(
			"Proxy Server",
			{"cluster": doc.cluster, "status": "Active"},
			pluck="name",
		)
		if len(proxy_servers) == 1 or (
			len(proxy_servers) > 1 and domain.default_proxy_server == proxy_server
		):
			"""
			If we have a single proxy server
			Or, in case of multiple proxy server, the site is using the default proxy server

			We can skip creating dns record
			"""
			return

	if is_standalone:
		_change_dns_record("UPSERT", domain, doc.server, record_name=record_name)
	else:
		_change_dns_record("UPSERT", domain, proxy_server, record_name=record_name)


def _change_dns_record(method: str, domain: RootDomain, proxy_server: str, record_name: str | None = None):
	"""
	Change dns record of site

	method: CREATE | DELETE | UPSERT
	"""
	if domain.generic_dns_provider:
		return

	client = boto3.client(
		"route53",
		aws_access_key_id=domain.aws_access_key_id,
		aws_secret_access_key=domain.get_password("aws_secret_access_key"),
	)
	try:
		zones = client.list_hosted_zones_by_name()["HostedZones"]
		hosted_zone = find(reversed(zones), lambda x: domain.name.endswith(x["Name"][:-1]))["Id"]
		client.change_resource_record_sets(
			ChangeBatch={
				"Changes": [
					{
						"Action": method,
						"ResourceRecordSet": {
							"Name": record_name,
							"Type": "CNAME",
							"TTL": 600,
							"ResourceRecords": [{"Value": proxy_server}],
						},
					}
				]
			},
			HostedZoneId=hosted_zone,
		)
	except client.exceptions.InvalidChangeBatch as e:
		# If we're attempting to DELETE and record is not found, ignore the error
		# e.response["Error"]["Message"] looks like
		# [Tried to delete resource record set [name='xxx.frappe.cloud.', type='CNAME'] but it was not found]
		if method == "DELETE" and "but it was not found" in e.response["Error"]["Message"]:
			return
		log_error(
			"Route 53 Record Creation Error",
			domain=domain.name,
			site=record_name,
			proxy_server=proxy_server,
		)
	except Exception:
		log_error(
			"Route 53 Record Creation Error",
			domain=domain.name,
			site=record_name,
			proxy_server=proxy_server,
		)
