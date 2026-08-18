# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import add_days, get_datetime_str, getdate, now_datetime

BYTES_PER_GB = 1024**3
# The blank scope means "the whole fleet", so rows without a scope need a name.
UNATTRIBUTED_SCOPE = "(none)"

# A driver is what the business was doing that day. Cloud usage that grows with its
# driver is the product working; cloud usage that grows without it is the thing worth
# waking someone for. Every driver here is measured from Press's own records, so it
# never depends on the provider agreeing with us.
DRIVER_ACTIVE_SITES = "Active Sites"
DRIVER_RUNNING_MACHINES = "Running Virtual Machines"
DRIVER_VOLUME_SIZE = "Attached Volume Size"
DRIVER_SNAPSHOT_SIZE = "Snapshot Size"
DRIVER_BACKUP_STORED = "Backup Bytes Stored"
DRIVER_BACKUP_UPLOADED = "Backup Bytes Uploaded"
DRIVER_BACKUP_OBJECTS = "Backup Objects Uploaded"

STORED_FIELDS = [
	"name",
	"creation",
	"modified",
	"owner",
	"modified_by",
	"date",
	"driver",
	"scope",
	"value",
	"unit",
]


class CloudUsageDriver(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date
		driver: DF.Data
		scope: DF.Data | None
		unit: DF.Data | None
		value: DF.Float
	# end: auto-generated types

	pass


def record(date, driver, rows, unit):
	"""Replace a driver's rows for one day. Rows are (scope, value) pairs; a blank
	scope is the fleet-wide figure the detectors compare against."""
	frappe.db.delete("Cloud Usage Driver", {"date": date, "driver": driver})
	if not rows:
		return

	timestamp = get_datetime_str(now_datetime())
	user = frappe.session.user
	values = [
		(
			frappe.generate_hash(length=10),
			timestamp,
			timestamp,
			user,
			user,
			date,
			driver,
			scope,
			value,
			unit,
		)
		for scope, value in rows
	]
	frappe.db.bulk_insert("Cloud Usage Driver", STORED_FIELDS, values)


def with_total(rows_by_scope):
	"""Per-scope rows plus the fleet-wide total under a blank scope.

	The blank scope is reserved for that total, because the detectors compare against it.
	A row that has no scope of its own — a bucket or cluster left unset — is named
	instead of silently merging into the total and doubling it.
	"""
	rows = [(scope or UNATTRIBUTED_SCOPE, value) for scope, value in rows_by_scope.items()]
	return [("", sum(rows_by_scope.values())), *rows]


def count_active_sites():
	return frappe.db.count("Site", {"status": "Active"})


def count_running_machines():
	return frappe.db.count("Virtual Machine", {"status": "Running"})


def get_attached_volume_size():
	"""Provisioned block storage on machines that still exist, in GB. A terminated
	machine whose volume survived is exactly the leak this is meant to expose, so the
	comparison against what AWS bills matters more than the number itself."""
	Volume = frappe.qb.DocType("Virtual Machine Volume")
	Machine = frappe.qb.DocType("Virtual Machine")

	result = (
		frappe.qb.from_(Volume)
		.inner_join(Machine)
		.on(Volume.parent == Machine.name)
		.select(Machine.cluster.as_("scope"), Sum(Volume.size).as_("size"))
		.where(Machine.status != "Terminated")
		.groupby(Machine.cluster)
	).run(as_dict=True)

	return {row.scope or "": row.size or 0 for row in result}


def get_snapshot_size():
	"""Snapshot storage Press believes it is holding, in GB. Snapshots that AWS bills
	for but Press no longer lists are the classic retention leak."""
	Snapshot = frappe.qb.DocType("Virtual Disk Snapshot")

	result = (
		frappe.qb.from_(Snapshot)
		.select(Snapshot.cluster.as_("scope"), Sum(Snapshot.size).as_("size"))
		.where(Snapshot.status == "Completed")
		.where(Snapshot.expired == 0)
		.groupby(Snapshot.cluster)
	).run(as_dict=True)

	return {row.scope or "": row.size or 0 for row in result}


def get_backup_bytes_stored():
	"""Bytes Press still expects to find in each bucket. Remote File rows are never
	deleted, only marked Unavailable, so this is the live set rather than the history."""
	RemoteFile = frappe.qb.DocType("Remote File")

	result = (
		frappe.qb.from_(RemoteFile)
		.select(RemoteFile.bucket.as_("scope"), Sum(RemoteFile.file_size).as_("size"))
		.where(RemoteFile.status == "Available")
		.groupby(RemoteFile.bucket)
	).run(as_dict=True)

	return {row.scope or "": row.size or 0 for row in result}


def collect_point_in_time_drivers(date=None):
	"""Drivers that can only be counted as they are now. They start accumulating the
	day this runs for the first time; there is no history to recover."""
	date = getdate(date) if date else getdate()

	record(date, DRIVER_ACTIVE_SITES, [("", count_active_sites())], "Nos")
	record(date, DRIVER_RUNNING_MACHINES, [("", count_running_machines())], "Nos")
	record(date, DRIVER_VOLUME_SIZE, with_total(get_attached_volume_size()), "GB")
	record(date, DRIVER_SNAPSHOT_SIZE, with_total(get_snapshot_size()), "GB")
	record(date, DRIVER_BACKUP_STORED, with_total(get_backup_bytes_stored()), "Bytes")


def collect_upload_drivers(start, end):
	"""Gross bytes and objects written to each backup bucket per day. CloudWatch only
	publishes net bucket size, which hides a doubling of uploads whenever deletion
	doubles with it — and hides a stalled reaper completely. Remote File rows carry
	their own creation date, so unlike the other drivers this one has full history."""
	RemoteFile = frappe.qb.DocType("Remote File")
	day = Date(RemoteFile.creation).as_("day")

	result = (
		frappe.qb.from_(RemoteFile)
		.select(
			day,
			RemoteFile.bucket.as_("scope"),
			Sum(RemoteFile.file_size).as_("size"),
			Count(RemoteFile.name).as_("objects"),
		)
		.where(RemoteFile.creation >= getdate(start))
		.where(RemoteFile.creation < getdate(end))
		.groupby(day, RemoteFile.bucket)
	).run(as_dict=True)

	bytes_by_date = {}
	objects_by_date = {}
	for row in result:
		date = getdate(row.day)
		bytes_by_date.setdefault(date, {})[row.scope or ""] = row.size or 0
		objects_by_date.setdefault(date, {})[row.scope or ""] = row.objects or 0

	for date, rows_by_scope in bytes_by_date.items():
		record(date, DRIVER_BACKUP_UPLOADED, with_total(rows_by_scope), "Bytes")
	for date, rows_by_scope in objects_by_date.items():
		record(date, DRIVER_BACKUP_OBJECTS, with_total(rows_by_scope), "Nos")


def collect_daily_drivers(date=None):
	date = getdate(date) if date else getdate()
	collect_point_in_time_drivers(date)
	collect_upload_drivers(add_days(date, -1), add_days(date, 1))


def backfill_upload_drivers(months=14):
	"""Rebuild the upload series from Remote File history, a month at a time so the
	group-by never spans the whole table."""
	end = add_days(getdate(), 1)
	for month in range(months):
		window_end = add_days(end, -30 * month)
		window_start = add_days(end, -30 * (month + 1))
		collect_upload_drivers(window_start, window_end)
		frappe.db.commit()
