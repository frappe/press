# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import boto3
from press.utils import log_error

DOMAIN_NAME = "erpnext.com"
PROXY_SERVER = "n2.frappe.cloud"


def get_active_domains():
	return frappe.get_all(
		"Site", {"status": ("!=", "Archived"), "domain": DOMAIN_NAME}, pluck="name"
	)


def get_dns_record_pages():
	try:
		domain = frappe.get_doc("Root Domain", DOMAIN_NAME)
		client = boto3.client(
			"route53",
			aws_access_key_id=domain.aws_access_key_id,
			aws_secret_access_key=domain.get_password("aws_secret_access_key"),
		)
		hosted_zone = client.list_hosted_zones_by_name(DNSName=domain.name)["HostedZones"][0][
			"Id"
		]
		paginator = client.get_paginator("list_resource_record_sets")
		return paginator.paginate(
			PaginationConfig={"MaxItems": 1000, "PageSize": 300, "StartingToken": "0"},
			HostedZoneId=hosted_zone.split("/")[-1],
		)
	except Exception:
		log_error(
			"Route 53 Pagination Error", domain=domain.name,
		)


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
		client = boto3.client(
			"route53",
			aws_access_key_id=domain.aws_access_key_id,
			aws_secret_access_key=domain.get_password("aws_secret_access_key"),
		)
		hosted_zone = client.list_hosted_zones_by_name(DNSName=domain.name)["HostedZones"][0][
			"Id"
		]
		client.change_resource_record_sets(
			ChangeBatch={"Changes": changes}, HostedZoneId=hosted_zone,
		)
	except Exception:
		log_error(
			"Route 53 Record Deletion Error", domain=domain.name,
		)
