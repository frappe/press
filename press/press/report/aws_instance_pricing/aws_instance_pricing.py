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
	if filters.cluster:
		clusters = [filters.cluster]
	else:
		clusters = frappe.get_all(
			"Cluster", filters={"public": 1, "cloud_provider": "AWS EC2"}, pluck="name"
		)
	data = []
	for cluster in clusters:
		data.extend(get_cluster_data(filters, cluster))
	return data


def get_cluster_data(filters, cluster_name):
	cluster = frappe.get_doc("Cluster", cluster_name)
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
				"cluster": cluster.name,
				"instance_type": product["product"]["attributes"]["instanceType"].split(".")[0],
				"instance": product["product"]["attributes"]["instanceType"],
				"vcpu": cint(product["product"]["attributes"]["vcpu"], 0),
				"memory": flt(product["product"]["attributes"]["memory"][:-4]),
			}
			for term in product["terms"].get("OnDemand", {}).values():
				row["on_demand"] = (
					flt(list(term["priceDimensions"].values())[0]["pricePerUnit"]["USD"]) * 750
				)
			instance_type = parse_instance_type(row["instance"])
			if not instance_type:
				continue

			family, generation, processor, size = instance_type

			row.update(
				{
					"family": family,
					"generation": generation,
					"processor": processor,
					"size": size,
					"size_multiplier": parse_size_multiplier(size),
				}
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

	rows.sort(key=lambda x: (x["instance_type"], x["vcpu"], x["memory"]))
	return rows


FAMILIES = [
	"c",
	"d",
	"f",
	"g",
	"hpc",
	"inf",
	"i",
	"mac",
	"m",
	"p",
	"r",
	"trn",
	"t",
	"u",
	"vt",
	"x",
]
PREFERRED_FAMILIES = [
	"c",
	"m",
	"r",
]
PROCESSORS = ["a", "g", "i"]


def parse_instance_type(instance_type):
	instance_type, size = instance_type.split(".")
	# Skip metal instances
	if "metal" in size:
		return

	family = None
	for ff in FAMILIES:
		if instance_type.startswith(ff):
			family = ff
			break

	# Ignore other instance families
	if family not in PREFERRED_FAMILIES:
		return

	rest = instance_type.removeprefix(family)
	generation = int(rest[0])
	rest = rest[1:]

	# If processor isn't mentioned, assume it's an Intel
	if rest and rest[0] in PROCESSORS:
		processor = rest[0]
		rest = rest[1:]
	else:
		processor = "i"

	if rest:
		return

	return family, generation, processor, size


def parse_size_multiplier(size):
	SIZES = {
		"medium": 1 / 4,
		"large": 1 / 2,
		"xlarge": 1,
	}
	if size in SIZES:
		return SIZES[size]
	else:
		size = size.removesuffix("xlarge")
		return float(size)
