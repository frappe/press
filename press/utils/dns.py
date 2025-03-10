from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
import frappe
from frappe.core.utils import find

from press.utils import log_error

if TYPE_CHECKING:
	from frappe.model.document import Document


@frappe.whitelist()
def create_dns_record(doc, record_name=None):
	"""Check if site needs dns records and creates one."""
	domain = frappe.get_doc("Root Domain", doc.domain)

	if domain.generic_dns_provider:
		return

	is_standalone = frappe.get_value("Server", doc.server, "is_standalone")
	if doc.cluster == domain.default_cluster and not is_standalone:
		return

	if is_standalone:
		_change_dns_record("UPSERT", domain, doc.server, record_name=record_name)
	else:
		proxy_server = frappe.get_value("Server", doc.server, "proxy_server")
		_change_dns_record("UPSERT", domain, proxy_server, record_name=record_name)


def _change_dns_record(method: str, domain: Document, proxy_server: str, record_name: str | None = None):
	"""
	Change dns record of site

	method: CREATE | DELETE | UPSERT
	"""
	try:
		if domain.generic_dns_provider:
			return

		client = boto3.client(
			"route53",
			aws_access_key_id=domain.aws_access_key_id,
			aws_secret_access_key=domain.get_password("aws_secret_access_key"),
		)
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
