# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import boto3
import frappe
from botocore.config import Config as BotoConfig
from hcloud import Client as HetznerClient

AWS_STATES = ["pending", "running", "stopping", "stopped", "shutting-down"]
DIGITAL_OCEAN_PAGE_SIZE = 200

# me-south-1 (Bahrain) is currently unreachable; TODO remove once AWS resolves it
# cn-north-1 (Beijing) is a separate AWS partition, needs separate credentials
EXCLUDED_AWS_REGIONS = {"me-south-1", "cn-north-1"}

AWS_CLIENT_CONFIG = BotoConfig(
	connect_timeout=10,
	read_timeout=20,
	retries={"max_attempts": 2, "mode": "standard"},
)


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = filters or {}
	provider = filters.get("provider")
	if not provider:
		frappe.throw("Select a Provider to run this report")

	columns = frappe.get_doc("Report", "Untracked Servers").get_columns()
	data = get_data(provider, filters.get("cluster"))
	return columns, data


def get_data(provider, cluster):
	if provider == "AWS EC2":
		return get_untracked_aws_instances(cluster)

	fetch_untracked = {
		"Hetzner": get_untracked_hetzner_servers,
		"DigitalOcean": get_untracked_digital_ocean_droplets,
	}[provider]

	clusters = [frappe.get_doc("Cluster", name) for name in get_clusters(provider, cluster)]
	rows = []
	for cluster_doc in clusters:
		rows.extend(get_cluster_rows(fetch_untracked, cluster_doc, provider))
	return rows


def get_cluster_rows(fetch_untracked, cluster, provider):
	try:
		return fetch_untracked(cluster)
	except Exception:
		frappe.log_error(title=f"Untracked Servers: Failed to fetch {cluster.name}")
		error = "Error: Could not fetch from provider (see Error Log)"
		return [get_status_row(provider, cluster.name, cluster.region, error)]


def get_status_row(provider, cluster_name, region, status):
	return {
		"provider": provider,
		"cluster": cluster_name,
		"instance_id": None,
		"name": None,
		"status": status,
		"instance_type": None,
		"region": region,
	}


def get_clusters(provider, cluster):
	filters = {"cloud_provider": provider}
	if cluster:
		filters["name"] = cluster
	return frappe.get_all("Cluster", filters, pluck="name")


def get_known_instance_ids(provider, **filters):
	filters.update({"cloud_provider": provider, "status": ("!=", "Terminated"), "instance_id": ("is", "set")})
	instance_ids = frappe.get_all("Virtual Machine", filters, pluck="instance_id")
	return {str(instance_id) for instance_id in instance_ids}


def get_untracked_aws_instances(cluster):
	press_settings = frappe.get_cached_doc("Press Settings")
	secret_key = press_settings.get_password("aws_secret_access_key", raise_exception=False)
	if not press_settings.aws_access_key_id or not secret_key:
		frappe.throw("AWS credentials are not configured on Press Settings")

	rows = []
	for region in get_aws_regions(cluster):
		rows.extend(get_region_rows(press_settings.aws_access_key_id, secret_key, region))
	return rows


def get_aws_regions(cluster):
	"""All AWS regions, so leaked instances in a region Press never registered still show up."""
	if cluster:
		region = frappe.db.get_value("Cluster", {"name": cluster, "cloud_provider": "AWS EC2"}, "region")
		return [region] if region else []
	return boto3.session.Session().get_available_regions("ec2", partition_name="aws")


def get_region_rows(access_key_id, secret_key, region):
	cluster_name = frappe.db.get_value("Cluster", {"cloud_provider": "AWS EC2", "region": region}, "name")
	if region in EXCLUDED_AWS_REGIONS:
		return [get_status_row("AWS EC2", cluster_name, region, "Skipped: region excluded")]

	try:
		return fetch_aws_region_instances(access_key_id, secret_key, region, cluster_name)
	except Exception:
		frappe.log_error(title=f"Untracked Servers: Failed to fetch {region}")
		error = "Error: Could not fetch from provider (see Error Log)"
		return [get_status_row("AWS EC2", cluster_name, region, error)]


def fetch_aws_region_instances(access_key_id, secret_key, region, cluster_name):
	client = boto3.client(
		"ec2",
		region_name=region,
		aws_access_key_id=access_key_id,
		aws_secret_access_key=secret_key,
		config=AWS_CLIENT_CONFIG,
	)
	known_instance_ids = get_known_instance_ids("AWS EC2", region=region)

	paginator = client.get_paginator("describe_instances")
	pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": AWS_STATES}])

	rows = []
	for page in pages:
		for reservation in page["Reservations"]:
			for instance in reservation["Instances"]:
				if instance["InstanceId"] in known_instance_ids:
					continue
				rows.append(
					{
						"provider": "AWS EC2",
						"cluster": cluster_name,
						"instance_id": instance["InstanceId"],
						"name": get_aws_name_tag(instance),
						"status": instance["State"]["Name"],
						"instance_type": instance["InstanceType"],
						"region": region,
					}
				)
	return rows


def get_aws_name_tag(instance):
	for tag in instance.get("Tags", []):
		if tag["Key"] == "Name":
			return tag["Value"]
	return None


def get_untracked_hetzner_servers(cluster):
	api_token = cluster.get_password("hetzner_api_token", raise_exception=False)
	if not api_token:
		frappe.throw(f"Hetzner API token is not configured on Cluster {cluster.name}")

	client = HetznerClient(token=api_token)
	known_instance_ids = get_known_instance_ids("Hetzner", cluster=cluster.name)

	rows = []
	for server in client.servers.get_all():
		if str(server.id) in known_instance_ids:
			continue
		rows.append(
			{
				"provider": "Hetzner",
				"cluster": cluster.name,
				"instance_id": str(server.id),
				"name": server.name,
				"status": server.status,
				"instance_type": server.server_type.name if server.server_type else None,
				"region": cluster.region,
			}
		)
	return rows


def get_untracked_digital_ocean_droplets(cluster):
	import pydo

	api_token = cluster.get_password("digital_ocean_api_token", raise_exception=False)
	if not api_token:
		frappe.throw(f"DigitalOcean API token is not configured on Cluster {cluster.name}")

	client = pydo.Client(token=api_token)
	known_instance_ids = get_known_instance_ids("DigitalOcean", cluster=cluster.name)

	rows = []
	page = 1
	while True:
		droplets = client.droplets.list(per_page=DIGITAL_OCEAN_PAGE_SIZE, page=page).get("droplets", [])
		for droplet in droplets:
			if str(droplet["id"]) in known_instance_ids:
				continue
			rows.append(
				{
					"provider": "DigitalOcean",
					"cluster": cluster.name,
					"instance_id": str(droplet["id"]),
					"name": droplet.get("name"),
					"status": droplet.get("status"),
					"instance_type": droplet.get("size_slug"),
					"region": cluster.region,
				}
			)
		if len(droplets) < DIGITAL_OCEAN_PAGE_SIZE:
			break
		page += 1
	return rows
