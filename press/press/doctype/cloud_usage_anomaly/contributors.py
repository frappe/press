# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Turning an anomalous usage type into the Press records behind it.

An alert that says "S3 is up" is a pager with no lead attached. Each resolver here
answers the next question — which buckets, whose teams, which machines — from Press's
own tables, so the drill-down works without asking AWS for resource-level data.
"""

import frappe
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import add_days, getdate

BYTES_PER_GB = 1024**3
CONTRIBUTOR_LIMIT = 5


def get_contributors(usage_type, region, changed_on):
	resolver = get_resolver(usage_type)
	if not resolver:
		return []

	try:
		return resolver(region, getdate(changed_on))
	except Exception:
		frappe.log_error(title="Cloud Cost Contributor Lookup Failed", message=usage_type)
		return []


def get_resolver(usage_type):
	usage_type = usage_type or ""
	for marker, resolver in RESOLVERS:
		if marker in usage_type:
			return resolver
	return None


def get_buckets_in_region(region):
	if not region:
		return []
	return frappe.get_all("Backup Bucket", {"region": region}, pluck="name")


def stored_backup_bytes(region, changed_on):
	"""Whose backups are sitting in the bucket right now."""
	RemoteFile = frappe.qb.DocType("Remote File")

	query = (
		frappe.qb.from_(RemoteFile)
		.select(RemoteFile.team, Sum(RemoteFile.file_size).as_("size"))
		.where(RemoteFile.status == "Available")
		.where(RemoteFile.team.isnotnull())
		.groupby(RemoteFile.team)
		.orderby(Sum(RemoteFile.file_size), order=frappe.qb.desc)
		.limit(CONTRIBUTOR_LIMIT)
	)
	buckets = get_buckets_in_region(region)
	if buckets:
		query = query.where(RemoteFile.bucket.isin(buckets))

	return [
		{
			"label": f"Backups stored by {row.team}",
			"document_type": "Team",
			"document_name": row.team,
			"team": row.team,
			"value": (row.size or 0) / BYTES_PER_GB,
			"unit": "GB",
		}
		for row in query.run(as_dict=True)
	]


def uploaded_backup_objects(region, changed_on):
	"""Who wrote to the bucket on the day it changed."""
	RemoteFile = frappe.qb.DocType("Remote File")

	query = (
		frappe.qb.from_(RemoteFile)
		.select(
			RemoteFile.team,
			Count(RemoteFile.name).as_("objects"),
			Sum(RemoteFile.file_size).as_("size"),
		)
		.where(Date(RemoteFile.creation) == changed_on)
		.where(RemoteFile.team.isnotnull())
		.groupby(RemoteFile.team)
		.orderby(Count(RemoteFile.name), order=frappe.qb.desc)
		.limit(CONTRIBUTOR_LIMIT)
	)
	buckets = get_buckets_in_region(region)
	if buckets:
		query = query.where(RemoteFile.bucket.isin(buckets))

	return [
		{
			"label": f"{row.objects} objects uploaded by {row.team}",
			"document_type": "Team",
			"document_name": row.team,
			"team": row.team,
			"value": row.objects,
			"unit": "Nos",
		}
		for row in query.run(as_dict=True)
	]


def uploaded_backup_bytes(region, changed_on):
	"""Transfer has no Press-side meter, so the bytes we pushed to backups stand in
	for it. Treat these as the largest movers that day, not as the transfer itself."""
	RemoteFile = frappe.qb.DocType("Remote File")

	query = (
		frappe.qb.from_(RemoteFile)
		.select(RemoteFile.team, Sum(RemoteFile.file_size).as_("size"))
		.where(Date(RemoteFile.creation) == changed_on)
		.where(RemoteFile.team.isnotnull())
		.groupby(RemoteFile.team)
		.orderby(Sum(RemoteFile.file_size), order=frappe.qb.desc)
		.limit(CONTRIBUTOR_LIMIT)
	)

	return [
		{
			"label": f"Backups uploaded by {row.team}",
			"document_type": "Team",
			"document_name": row.team,
			"team": row.team,
			"value": (row.size or 0) / BYTES_PER_GB,
			"unit": "GB",
		}
		for row in query.run(as_dict=True)
	]


def snapshot_storage(region, changed_on):
	"""Machines holding the most snapshot storage, and how old the pile is. A machine
	whose snapshots stretch back past its retention window is a reaper that stopped."""
	Snapshot = frappe.qb.DocType("Virtual Disk Snapshot")

	query = (
		frappe.qb.from_(Snapshot)
		.select(
			Snapshot.virtual_machine,
			Sum(Snapshot.size).as_("size"),
			Count(Snapshot.name).as_("snapshots"),
		)
		.where(Snapshot.status == "Completed")
		.where(Snapshot.expired == 0)
		.where(Snapshot.virtual_machine.isnotnull())
		.groupby(Snapshot.virtual_machine)
		.orderby(Sum(Snapshot.size), order=frappe.qb.desc)
		.limit(CONTRIBUTOR_LIMIT)
	)
	if region:
		query = query.where(Snapshot.region == region)

	rows = query.run(as_dict=True)
	teams = get_machine_teams([row.virtual_machine for row in rows])

	return [
		{
			"label": f"{row.snapshots} snapshots on {row.virtual_machine}",
			"document_type": "Virtual Machine",
			"document_name": row.virtual_machine,
			"team": teams.get(row.virtual_machine),
			"value": row.size or 0,
			"unit": "GB",
		}
		for row in rows
	]


def volume_storage(region, changed_on):
	"""Machines carrying the most block storage."""
	Volume = frappe.qb.DocType("Virtual Machine Volume")
	Machine = frappe.qb.DocType("Virtual Machine")

	query = (
		frappe.qb.from_(Volume)
		.inner_join(Machine)
		.on(Volume.parent == Machine.name)
		.select(Machine.name.as_("machine"), Machine.team, Sum(Volume.size).as_("size"))
		.where(Machine.status != "Terminated")
		.groupby(Machine.name, Machine.team)
		.orderby(Sum(Volume.size), order=frappe.qb.desc)
		.limit(CONTRIBUTOR_LIMIT)
	)
	if region:
		query = query.where(Machine.region == region)

	return [
		{
			"label": f"Volumes on {row.machine}",
			"document_type": "Virtual Machine",
			"document_name": row.machine,
			"team": row.team,
			"value": row.size or 0,
			"unit": "GB",
		}
		for row in query.run(as_dict=True)
	]


def machines_created_around(region, changed_on):
	"""Compute steps up when machines are added, so the machines added that day are
	the answer far more often than the ones that were already running."""
	filters = {
		"creation": ("between", [add_days(changed_on, -1), add_days(changed_on, 1)]),
		"status": ("!=", "Terminated"),
	}
	if region:
		filters["region"] = region

	machines = frappe.get_all(
		"Virtual Machine",
		filters,
		["name", "team", "machine_type", "vcpu"],
		order_by="creation desc",
		limit=CONTRIBUTOR_LIMIT,
	)

	return [
		{
			"label": f"{machine.machine_type} created on {changed_on}",
			"document_type": "Virtual Machine",
			"document_name": machine.name,
			"team": machine.team,
			"value": machine.vcpu or 0,
			"unit": "vCPU",
		}
		for machine in machines
	]


def get_machine_teams(machines):
	if not machines:
		return {}

	rows = frappe.get_all("Virtual Machine", {"name": ("in", machines)}, ["name", "team"])
	return {row.name: row.team for row in rows}


# Ordered: the first marker found in the usage type wins, so put the specific ones first.
RESOLVERS = [
	("EBS:SnapshotUsage", snapshot_storage),
	("EBS:VolumeUsage", volume_storage),
	("EBS:VolumeP-IOPS", volume_storage),
	("BoxUsage", machines_created_around),
	("SpotUsage", machines_created_around),
	("DedicatedUsage", machines_created_around),
	("TimedStorage", stored_backup_bytes),
	("Requests-Tier", uploaded_backup_objects),
	("DataTransfer", uploaded_backup_bytes),
	("NatGateway", uploaded_backup_bytes),
]
