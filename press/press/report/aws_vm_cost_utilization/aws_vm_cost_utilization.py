# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json

import boto3
import frappe
from frappe.utils import flt
from frappe.utils.caching import redis_cache

SERVER_TYPES = [
	"Server",
	"Database Server",
	"Proxy Server",
	"Log Server",
	"Monitor Server",
	"Registry Server",
	"Trace Server",
	"Analytics Server",
	"NFS Server",
	"NAT Server",
	"Bastion Server",
]

HOURS_PER_MONTH = 750
BILLABLE_STATES = ["pending", "running", "stopping", "stopped", "shutting-down"]

# Bahrain (unreachable), Beijing (separate AWS China partition, priced in CNY not USD).
EXCLUDED_REGIONS = ["me-south-1", "cn-north-1"]


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = filters or {}
	columns = frappe.get_doc("Report", "AWS VM Cost Utilization").get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	return columns, data, None, None, report_summary


def get_data(filters):
	instances = get_aws_instances(filters)
	press_vms = get_press_virtual_machines([instance["instance_id"] for instance in instances])
	server_by_vm = get_server_by_virtual_machine()

	rows = [
		build_row(instance, press_vms.get(instance["instance_id"]), server_by_vm) for instance in instances
	]
	rows.sort(key=lambda row: (row["tracked_in_press"], -row["estimated_monthly_cost"]))
	return rows


def build_row(instance, vm, server_by_vm):
	server = server_by_vm.get(vm.name) if vm else None
	is_running = instance["aws_status"] == "running"
	active_in_production = bool(is_running and server and server.status == "Active")

	monthly_cost = 0
	if is_running:
		monthly_cost = get_monthly_price(instance["instance_type"], instance["region"])

	return {
		"instance_id": instance["instance_id"],
		"name_tag": instance["name_tag"],
		"cluster": instance["cluster"],
		"region": instance["region"],
		"instance_type": instance["instance_type"],
		"aws_status": instance["aws_status"],
		"tracked_in_press": bool(vm),
		"virtual_machine": vm.name if vm else None,
		"press_status": vm.status if vm else None,
		"server_type": server.server_type if server else None,
		"server": server.name if server else None,
		"team": server.team if server else None,
		"active_in_production": active_in_production,
		"estimated_monthly_cost": monthly_cost,
	}


def get_aws_instances(filters):
	if filters.get("cluster"):
		clusters = [filters["cluster"]]
	else:
		clusters = frappe.get_all("Cluster", {"cloud_provider": "AWS EC2"}, pluck="name")

	instances = {}
	for cluster_name in clusters:
		for instance in get_cluster_instances(cluster_name, filters):
			# A misconfigured account could list the same instance under two clusters; keep one.
			instances[instance["instance_id"]] = instance
	return list(instances.values())


def get_cluster_instances(cluster_name, filters):
	cluster = frappe.get_doc("Cluster", cluster_name)
	secret_key = cluster.get_password("aws_secret_access_key", raise_exception=False)
	if not cluster.aws_access_key_id or not secret_key:
		frappe.throw(f"AWS credentials are not configured on Cluster {cluster_name}")

	client = boto3.client(
		"ec2",
		region_name=cluster.region,
		aws_access_key_id=cluster.aws_access_key_id,
		aws_secret_access_key=secret_key,
	)

	states = [filters["aws_status"]] if filters.get("aws_status") else BILLABLE_STATES
	paginator = client.get_paginator("describe_instances")
	pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": states}])

	instances = []
	for page in pages:
		for reservation in page["Reservations"]:
			for instance in reservation["Instances"]:
				instances.append(
					{
						"instance_id": instance["InstanceId"],
						"name_tag": get_name_tag(instance),
						"cluster": cluster.name,
						"region": cluster.region,
						"instance_type": instance["InstanceType"],
						"aws_status": instance["State"]["Name"],
					}
				)
	return instances


def get_name_tag(instance):
	for tag in instance.get("Tags", []):
		if tag["Key"] == "Name":
			return tag["Value"]
	return None


def get_press_virtual_machines(instance_ids):
	if not instance_ids:
		return {}
	vms = frappe.get_all(
		"Virtual Machine",
		{"instance_id": ("in", instance_ids)},
		["name", "instance_id", "status"],
	)
	return {vm.instance_id: vm for vm in vms}


def get_server_by_virtual_machine():
	server_by_vm = {}
	for server_type in SERVER_TYPES:
		fields = ["name", "virtual_machine", "status"]
		if frappe.get_meta(server_type).has_field("team"):
			fields.append("team")
		for server in frappe.get_all(server_type, {"virtual_machine": ("is", "set")}, fields):
			server_by_vm[server.virtual_machine] = frappe._dict(
				name=server.name,
				server_type=server_type,
				status=server.status,
				team=server.get("team"),
			)
	return server_by_vm


def get_pricing_client():
	settings = frappe.get_single("Press Settings")
	secret_key = settings.get_password("aws_secret_access_key", raise_exception=False)
	if not settings.aws_access_key_id or not secret_key:
		frappe.throw("AWS credentials are not configured in Press Settings")

	return boto3.client(
		"pricing",
		region_name="ap-south-1",
		aws_access_key_id=settings.aws_access_key_id,
		aws_secret_access_key=secret_key,
	)


@redis_cache(ttl=24 * 60 * 60)
def get_monthly_price(machine_type, region):
	client = get_pricing_client()
	product_filters = [
		{"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
		{"Type": "TERM_MATCH", "Field": "instanceType", "Value": machine_type},
		{"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
		{"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
		{"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
		{"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
	]

	price = 0
	response = client.get_products(ServiceCode="AmazonEC2", Filters=product_filters, MaxResults=1)
	for item in response["PriceList"]:
		product = json.loads(item)
		for term in product["terms"].get("OnDemand", {}).values():
			dimension = next(iter(term["priceDimensions"].values()))
			usd_price = dimension["pricePerUnit"].get("USD")
			# AWS China regions (e.g. cn-north-1) price only in CNY; skip rather than misreport.
			if usd_price is not None:
				price = flt(usd_price) * HOURS_PER_MONTH

	return price


def get_report_summary(rows):
	total_cost = sum(row["estimated_monthly_cost"] for row in rows)
	active_cost = sum(row["estimated_monthly_cost"] for row in rows if row["active_in_production"])
	untracked_rows = [row for row in rows if not row["tracked_in_press"]]
	untracked_cost = sum(row["estimated_monthly_cost"] for row in untracked_rows)

	return [
		{
			"value": total_cost,
			"label": "Total Estimated Monthly Cost (USD)",
			"datatype": "Currency",
			"indicator": "blue",
		},
		{
			"value": active_cost,
			"label": "Active (Production) Cost (USD)",
			"datatype": "Currency",
			"indicator": "green",
		},
		{
			"value": total_cost - active_cost,
			"label": "Idle / Inactive Cost (USD)",
			"datatype": "Currency",
			"indicator": "orange",
		},
		{
			"value": untracked_cost,
			"label": "Untracked In Press (USD)",
			"datatype": "Currency",
			"indicator": "red",
		},
		{
			"value": len(untracked_rows),
			"label": "Untracked Instances",
			"datatype": "Int",
			"indicator": "red",
		},
	]
