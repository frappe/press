import frappe
from press.press.doctype.cloud_region.cloud_region import CloudRegion

from press.utils import get_current_team


@frappe.whitelist()
def options():
	return {
		"cloud_providers": [
			{
				"name": "AWS EC2",
				"title": "Amazon Web Services (AWS)",
			},
			{
				"name": "OCI",
				"title": "Oracle Cloud Infrastructure (OCI)",
			},
		],
		"regions": CloudRegion.get_cloud_regions(),
	}


def ssh_key():
	return frappe.db.get_value("SSH Key", filters={"default": 1, "enabled": 1})


@frappe.whitelist()
def new(cluster):
	team = get_current_team(get_doc=True)
	# validate_team(team)
	cluster = frappe._dict(cluster)

	cluster.update(
		{
			"team": team.name,
			"ssh_key": ssh_key(),
			"__newname": f"{cluster.title}-{cluster.region}",
			"subnet_cidr_block": cluster.cidr_block,
		}
	)

	try:
		new_cluster = frappe.new_doc("Cluster", **cluster)
		new_cluster.insert()

		return new_cluster
	except Exception as e:
		frappe.throw(str(e))


def validate_team(team):
	if not team:
		frappe.throw("You must be part of a team to create a cluster")

	if not team.get("is_cluster_awllowed"):
		frappe.throw("Your team is not allowed to create clusters")


@frappe.whitelist()
def get_security_groups_information(cluster):
	cluster = frappe.get_cached_doc("Cluster", cluster)

	security_group_rules = cluster.describe_aws_security_group(
		group_id=cluster.security_group_id
	)
	proxy_security_group_rules = cluster.describe_aws_security_group(
		group_id=cluster.proxy_security_group_id
	)

	return {
		"security_group_id": cluster.security_group_id,
		"security_group_name": security_group_rules["GroupName"],
		"security_group_description": security_group_rules["Description"],
		"security_group_rules": security_group_rules["IpPermissions"],
		"proxy_security_group_id": cluster.proxy_security_group_id,
		"proxy_security_group_name": proxy_security_group_rules["GroupName"],
		"proxy_security_group_description": proxy_security_group_rules["Description"],
		"proxy_security_group_rules": proxy_security_group_rules["IpPermissions"],
	}
