# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
from frappe.core.utils import find
import json
import boto3


def execute(filters=None):
	frappe.only_for("System Manager")
	data = get_data(filters)
	columns = frappe.get_doc("Report", "AWS Instance Pricing").get_columns()
	return columns, data


def get_data(filters):
	cluster = frappe.get_doc("Cluster", filters.cluster)
	client = boto3.client(
		"pricing",
		region_name="ap-south-1",
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

	if filters.instance_family:
		product_filters.append(
			{
				"Type": "TERM_MATCH",
				"Field": "instanceFamily",
				"Value": filters.instance_family,
			}
		)

	if not filters.instance_store:
		product_filters.append(
			{"Type": "TERM_MATCH", "Field": "storage", "Value": "EBS only"}
		)

	response_iterator = paginator.paginate(
		ServiceCode="AmazonEC2", Filters=product_filters, PaginationConfig={"PageSize": 100}
	)
	rows = []
	for response in response_iterator:
		for item in response["PriceList"]:
			product = json.loads(item)
			if (
				filters.enhanced_networking
				and "n." not in product["product"]["attributes"]["instanceType"]
			):
				continue
			if (
				not filters.enhanced_networking
				and "n." in product["product"]["attributes"]["instanceType"]
			):
				continue

			if filters.processor:
				if filters.processor not in product["product"]["attributes"]["physicalProcessor"]:
					continue

			row = {
				"instance_type": product["product"]["attributes"]["instanceType"].split(".")[0],
				"instance": product["product"]["attributes"]["instanceType"],
				"vcpu": cint(product["product"]["attributes"]["vcpu"], 0),
				"memory": flt(product["product"]["attributes"]["memory"][:-4]),
			}
			for term in product["terms"].get("OnDemand", {}).values():
				row["on_demand"] = (
					flt(list(term["priceDimensions"].values())[0]["pricePerUnit"]["USD"]) * 750
				)
			for term in product["terms"].get("Reserved", {}).values():
				if (
					term["termAttributes"]["OfferingClass"] == "standard"
					and term["termAttributes"]["PurchaseOption"] == "No Upfront"
				):
					if term["termAttributes"]["LeaseContractLength"] == "1yr":
						row["1yr_reserved"] = (
							flt(list(term["priceDimensions"].values())[0]["pricePerUnit"]["USD"]) * 750
						)
					if term["termAttributes"]["LeaseContractLength"] == "3yr":
						row["3yr_reserved"] = (
							flt(list(term["priceDimensions"].values())[0]["pricePerUnit"]["USD"]) * 750
						)
			rows.append(row)

	client = boto3.client(
		"savingsplans",
		aws_access_key_id=cluster.aws_access_key_id,
		aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
	)

	response = client.describe_savings_plans_offering_rates(
		savingsPlanPaymentOptions=["No Upfront"],
		savingsPlanTypes=["Compute", "EC2Instance"],
		products=["EC2"],
		serviceCodes=["AmazonEC2"],
		filters=[
			{"name": "tenancy", "values": ["shared"]},
			{"name": "region", "values": [cluster.region]},
			{"name": "instanceType", "values": [row["instance"] for row in rows]},
			{"name": "productDescription", "values": ["Linux/UNIX"]},
		],
	)

	for rate in response["searchResults"]:
		if "BoxUsage" in rate["usageType"]:
			instance = find(rate["properties"], lambda x: x["name"] == "instanceType")["value"]
			row = find(rows, lambda x: x["instance"] == instance)
			years = rate["savingsPlanOffering"]["durationSeconds"] // 31536000
			plan = (
				"compute" if rate["savingsPlanOffering"]["planType"] == "Compute" else "instance"
			)
			row[f"{years}yr_{plan}"] = flt(rate["rate"]) * 750

	rows.sort(key=lambda x: (x["instance_type"], x["vcpu"]))
	return rows
