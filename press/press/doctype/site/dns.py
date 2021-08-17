# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.utils import log_error

DOMAIN_NAME = "erpnext.com"
PROXY_SERVER = "n2.frappe.cloud"

# get dns records
# collect domain from dns record not in active
# delete dns records

def cleanup():
	for page in get_dns_record_pages():
		to_delete = []

		frappe.db.commit()
		active = get_active_domains()

		for record in page["ResourceRecordSets"]:
			if (
				record["Type"] == "CNAME" and record["ResourceRecords"][0]["Value"] == PROXY_SERVER
			):
				domain = record["Name"].strip(".")
				if domain not in active:
					to_delete.append(domain)
		if to_delete:
			delete_dns_records(to_delete)


def get_active_domains():
	return frappe.get_all(
		"Site", {"status": ("!=", "Archived"), "domain": DOMAIN_NAME}, pluck="name"
	)


def get_dns_record_pages():
	try:
		domain = frappe.get_doc("Root Domain", DOMAIN_NAME)
		paginator = domain.boto3_client.get_paginator("list_resource_record_sets")
		return paginator.paginate(
			PaginationConfig={"MaxItems": 1000, "PageSize": 300, "StartingToken": "0"},
			HostedZoneId=domain.hosted_zone.split("/")[-1],
		)
	except Exception:
		log_error(
			"Route 53 Pagination Error", domain=domain.name,
		)


def delete_dns_records(records):
	try:
		changes = []
		for record in records:
			changes.append(
				{
					"Action": "DELETE",
					"ResourceRecordSet": {
						"Name": record,
						"Type": "CNAME",
						"TTL": 60,
						"ResourceRecords": [{"Value": PROXY_SERVER}],
					},
				}
			)

		domain = frappe.get_doc("Root Domain", DOMAIN_NAME)
		domain.boto3_client.change_resource_record_sets(
			ChangeBatch={"Changes": changes}, HostedZoneId=domain.hosted_zone,
		)

	except Exception:
		log_error(
			"Route 53 Record Deletion Error", domain=domain.name,
		)
