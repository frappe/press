# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
import json
import boto3


def execute(filters=None):
	frappe.only_for("System Manager")
	data = get_data(filters)
	columns = [
		{
			"fieldname": "instance",
			"fieldtype": "Data",
			"label": "Instance",
		},
		{
			"fieldname": "instance_type",
			"fieldtype": "Data",
			"label": "Instance Type",
		},
		{
			"fieldname": "vcpu",
			"fieldtype": "Int",
			"label": "vCPU",
		},
		{
			"fieldname": "memory",
			"fieldtype": "Float",
			"label": "Memory",
		},
	]
	return columns, data


def get_data(filters):
	cluster = frappe.get_doc("Cluster", filters.cluster)
	client = boto3.client(
		"pricing",
		region_name=cluster.region,
		aws_access_key_id=cluster.aws_access_key_id,
		aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
	)

	paginator = client.get_paginator("get_products")

	product_filters = [
		{"Type": "TERM_MATCH", "Field": "regionCode", "Value": cluster.region},
		{"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
		{"Type": "TERM_MATCH", "Field": "currentGeneration", "Value": "Yes"},
		{"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
		{"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
		{"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
	]

	response_iterator = paginator.paginate(
		ServiceCode="AmazonEC2", Filters=product_filters, PaginationConfig={"PageSize": 100}
	)
	rows = []
	for response in response_iterator:
		for item in response["PriceList"]:
			product = json.loads(item)
			row = {
				"instance_type": product["product"]["attributes"]["instanceType"].split(".")[0],
				"instance": product["product"]["attributes"]["instanceType"],
				"vcpu": cint(product["product"]["attributes"]["vcpu"], 0),
				"memory": flt(product["product"]["attributes"]["memory"][:-4]),
			}
			rows.append(row)

	return rows
