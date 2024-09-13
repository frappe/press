# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
import boto3


def execute(filters=None):
	frappe.only_for("System Manager")
	columns = frappe.get_doc("Report", "AWS Rightsizing Recommendation").get_columns()
	resource_type = filters.get("resource_type")
	data = get_data(resource_type)
	return columns, data


def get_data(resource_type):
	settings = frappe.get_single("Press Settings")
	client = boto3.client(
		"cost-optimization-hub",
		region_name="us-east-1",
		aws_access_key_id=settings.aws_access_key_id,
		aws_secret_access_key=settings.get_password("aws_secret_access_key"),
	)

	resource_types = {
		"Compute": ["Ec2Instance"],
		"Storage": ["EbsVolume"],
	}.get(resource_type, ["Ec2Instance", "EbsVolume"])

	paginator = client.get_paginator("list_recommendations")
	response_iterator = paginator.paginate(
		filter={
			"resourceTypes": resource_types,
			"actionTypes": ["Rightsize"],
		},
	)

	results = []
	for response in response_iterator:
		for row in response["items"]:
			resource_type = {
				"Ec2Instance": "Virtual Machine",
				"EbsVolume": "Virtual Machine Volume",
			}[row["currentResourceType"]]

			if resource_type == "Virtual Machine":
				virtual_machine = frappe.get_all(
					resource_type, {"instance_id": row["resourceId"]}, pluck="name"
				)
			elif resource_type == "Virtual Machine Volume":
				virtual_machine = frappe.get_all(
					resource_type, {"volume_id": row["resourceId"]}, pluck="parent"
				)

			if not virtual_machine:
				# This resource is not managed by Press. Ignore
				continue
			virtual_machine = virtual_machine[0]

			server_type = {
				"f": "Server",
				"m": "Database Server",
				"n": "Proxy Server",
			}[frappe.db.get_value("Virtual Machine", virtual_machine, "series")]

			server = frappe.db.get_value(
				server_type,
				{"virtual_machine": virtual_machine},
				["name", "team", "public"],
				as_dict=True,
			)
			data = {
				"resource_type": resource_type,
				"virtual_machine": virtual_machine,
				"server_type": server_type,
				"server": server.name,
				"team": server.team,
				"public": server.public,
				"region": row["region"],
				"estimated_cost": row["estimatedMonthlyCost"],
				"estimated_savings": row["estimatedMonthlySavings"],
				"estimated_savings_percentage": row["estimatedSavingsPercentage"],
				"current_usage": row["currentResourceSummary"],
				"recommended_usage": row["recommendedResourceSummary"],
				"currency": "USD",
			}

			if resource_type == "Virtual Machine":
				data["current_instance_type"] = row["currentResourceSummary"]
				data["recommended_instance_type"] = row["recommendedResourceSummary"]
			elif resource_type == "Virtual Machine Volume":
				# Splits "99.0 GB Storage/3000.0 IOPS/125.0 MB/s Throughput" into
				# ["99.0 GB Storage", "3000.0 IOPS", "125.0 MB", "/s Throughput"]
				_, iops, throughput, _ = row["currentResourceSummary"].split("/")
				data["current_iops"] = iops.split()[0]
				data["current_throughput"] = throughput.split()[0]

				_, iops, throughput, _ = row["recommendedResourceSummary"].split("/")
				data["recommended_iops"] = iops.split()[0]
				data["recommended_throughput"] = throughput.split()[0]

			results.append(data)
	results.sort(key=lambda x: x["estimated_savings"], reverse=True)
	return results
