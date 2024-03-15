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
