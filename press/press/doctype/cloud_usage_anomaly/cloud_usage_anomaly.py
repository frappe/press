# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate

from press.press.doctype.cloud_usage_anomaly.contributors import get_contributors
from press.press.doctype.cloud_usage_anomaly.detectors import (
	change_percent,
	detect_level_shift,
	detect_spike,
	mean,
)
from press.press.doctype.cloud_usage_driver.cloud_usage_driver import (
	DRIVER_ACTIVE_SITES,
	DRIVER_BACKUP_OBJECTS,
	DRIVER_BACKUP_STORED,
	DRIVER_RUNNING_MACHINES,
	DRIVER_SNAPSHOT_SIZE,
	DRIVER_VOLUME_SIZE,
)
from press.press.doctype.telegram_message.telegram_message import TelegramMessage

DAYS_PER_MONTH = 30

# What each kind of usage is expected to grow with. Ordered: the first marker found in
# the usage type wins, so the specific markers come before the general ones.
DRIVER_FOR_USAGE_TYPE = [
	("EBS:SnapshotUsage", DRIVER_SNAPSHOT_SIZE),
	("EBS:VolumeUsage", DRIVER_VOLUME_SIZE),
	("EBS:VolumeP-IOPS", DRIVER_VOLUME_SIZE),
	("BoxUsage", DRIVER_RUNNING_MACHINES),
	("SpotUsage", DRIVER_RUNNING_MACHINES),
	("DedicatedUsage", DRIVER_RUNNING_MACHINES),
	("TimedStorage", DRIVER_BACKUP_STORED),
	("Requests-Tier", DRIVER_BACKUP_OBJECTS),
	("DataTransfer", DRIVER_ACTIVE_SITES),
	("NatGateway", DRIVER_ACTIVE_SITES),
]


class CloudUsageAnomaly(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.cloud_usage_anomaly_contributor.cloud_usage_anomaly_contributor import (
			CloudUsageAnomalyContributor,
		)

		account: DF.Data | None
		baseline_value: DF.Float
		change_percent: DF.Percent
		changed_on: DF.Date | None
		contributors: DF.Table[CloudUsageAnomalyContributor]
		current_value: DF.Float
		daily_cost_impact: DF.Currency
		detected_on: DF.Date | None
		detector: DF.Literal["Spike", "Level Shift"]
		driver: DF.Data | None
		driver_change_percent: DF.Percent
		metric: DF.Literal["Usage", "Cost"]
		monthly_cost_impact: DF.Currency
		region: DF.Data | None
		series_key: DF.Data
		service: DF.Data | None
		status: DF.Literal["Open", "Acknowledged", "Resolved", "False Positive"]
		summary: DF.SmallText | None
		unit: DF.Data | None
		usage_type: DF.Data | None
		verdict: DF.Literal["Inorganic", "Organic", "No Driver"]
	# end: auto-generated types

	pass


def series_key(row):
	return " / ".join(part for part in [row.service, row.usage_type, row.region] if part)


def get_cost_series(start, end):
	"""Every day's cost and usage, grouped into one series per account, service, usage
	type and region."""
	rows = frappe.get_all(
		"Cloud Cost Daily",
		{"date": ("between", [start, end])},
		[
			"date",
			"account",
			"service",
			"usage_type",
			"region",
			"amortized_cost",
			"usage_quantity",
			"usage_unit",
		],
		order_by="date asc",
		limit_page_length=0,
	)

	series = {}
	for row in rows:
		key = (row.account, series_key(row))
		series.setdefault(key, []).append(row)
	return series


def get_driver_series(start, end):
	rows = frappe.get_all(
		"Cloud Usage Driver",
		{"date": ("between", [start, end]), "scope": ("in", ["", None])},
		["date", "driver", "value"],
		order_by="date asc",
		limit_page_length=0,
	)

	series = {}
	for row in rows:
		series.setdefault(row.driver, []).append({"date": getdate(row.date), "value": flt(row.value)})
	return series


def driver_for(usage_type):
	usage_type = usage_type or ""
	for marker, driver in DRIVER_FOR_USAGE_TYPE:
		if marker in usage_type:
			return driver
	return None


def fill_missing_days(points_by_date, start, end):
	"""Cost Explorer omits days a series did not bill on. Left as gaps they read as a
	drop and then a recovery, so absent days are the zero they actually were."""
	points = []
	date = getdate(start)
	end = getdate(end)
	while date <= end:
		points.append({"date": date, "value": points_by_date.get(date, 0)})
		date = add_days(date, 1)
	return points


def split_mean_change(points, changed_on):
	"""Mean before the change against mean from the change onward."""
	before = [point["value"] for point in points if point["date"] < changed_on]
	after = [point["value"] for point in points if point["date"] >= changed_on]
	if not before or not after:
		return None
	return {"baseline": mean(before), "current": mean(after)}


def get_dismissed_dates(account, key):
	"""Days an operator has already called a false alarm. Left in the baseline, a
	one-off migration keeps the median wrong for a month."""
	rows = frappe.get_all(
		"Cloud Usage Anomaly",
		{"account": account, "series_key": key, "detector": "Spike", "status": "False Positive"},
		pluck="changed_on",
	)
	return {getdate(date) for date in rows if date}


def choose_metric(rows):
	"""Usage quantity where AWS reports it, cost otherwise. Detecting on usage keeps a
	price change from being reported as someone consuming more."""
	quantities = [flt(row.usage_quantity) for row in rows]
	if any(quantities):
		return "Usage", rows[0].usage_unit or ""
	return "Cost", "USD"


def build_anomaly(account, key, rows, settings, drivers, start, end):
	metric, unit = choose_metric(rows)
	dismissed = get_dismissed_dates(account, key)

	value_field = "usage_quantity" if metric == "Usage" else "amortized_cost"
	measured = {getdate(row.date): flt(row.get(value_field)) for row in rows}
	costs = {getdate(row.date): flt(row.amortized_cost) for row in rows}

	points = [point for point in fill_missing_days(measured, start, end) if point["date"] not in dismissed]
	cost_points = fill_missing_days(costs, start, end)

	if mean([point["value"] for point in cost_points]) < flt(settings.minimum_series_cost):
		return None

	# Level shift first. A series that settled at a new number weeks ago still reads as
	# a loud day every single morning, and answering "it was high yesterday" when the
	# real answer is "it changed on the twelfth" is the whole failure this replaces.
	found = detect_level_shift(points, flt(settings.level_shift_minimum_change) or 20)
	detector = "Level Shift"
	if not found:
		found = detect_spike(points, flt(settings.spike_mad_threshold) or 3)
		detector = "Spike"
	if not found:
		return None

	impact = split_mean_change(cost_points, found["changed_on"])
	daily_cost_impact = impact["current"] - impact["baseline"] if impact else 0
	if daily_cost_impact < flt(settings.minimum_daily_cost_impact):
		return None

	sample = rows[0]
	anomaly = {
		"account": account,
		"series_key": key,
		"service": sample.service,
		"usage_type": sample.usage_type,
		"region": sample.region,
		"detector": detector,
		"metric": metric,
		"unit": unit,
		"changed_on": found["changed_on"],
		"detected_on": getdate(),
		"baseline_value": found["baseline"],
		"current_value": found["current"],
		"change_percent": found["change_percent"],
		"daily_cost_impact": daily_cost_impact,
		"monthly_cost_impact": daily_cost_impact * DAYS_PER_MONTH,
	}
	anomaly.update(judge(sample.usage_type, drivers, found, settings))
	anomaly["summary"] = describe(anomaly)
	return anomaly


def judge(usage_type, drivers, found, settings):
	"""Growth that its driver kept up with is the product working. Growth its driver
	did not follow is the alert."""
	driver = driver_for(usage_type)
	points = drivers.get(driver) if driver else None
	if not points:
		return {"driver": driver, "driver_change_percent": 0, "verdict": "No Driver"}

	movement = split_mean_change(points, found["changed_on"])
	if not movement:
		return {"driver": driver, "driver_change_percent": 0, "verdict": "No Driver"}

	driver_percent = change_percent(movement["baseline"], movement["current"])
	tolerance = flt(settings.organic_tolerance)
	organic = driver_percent >= found["change_percent"] - tolerance

	return {
		"driver": driver,
		"driver_change_percent": driver_percent,
		"verdict": "Organic" if organic else "Inorganic",
	}


def describe(anomaly):
	lines = [
		f"{anomaly['series_key']} {'stepped' if anomaly['detector'] == 'Level Shift' else 'spiked'} "
		f"from {anomaly['baseline_value']:,.2f} to {anomaly['current_value']:,.2f} "
		f"{anomaly['unit']} on {anomaly['changed_on']} ({anomaly['change_percent']:+.1f}%).",
		f"Costing about ${anomaly['daily_cost_impact']:,.2f} a day more "
		f"(${anomaly['monthly_cost_impact']:,.0f} a month).",
	]
	if anomaly["verdict"] == "No Driver":
		lines.append("No business driver is mapped to this usage type, so it cannot be explained away.")
	else:
		lines.append(
			f"{anomaly['driver']} moved {anomaly['driver_change_percent']:+.1f}% over the same days, "
			f"so this reads as {anomaly['verdict'].lower()}."
		)
	return "\n".join(lines)


def save_anomaly(anomaly):
	"""One live record per series and detector, refreshed in place. A level shift that
	keeps growing should sharpen the same finding, not file a new one every morning."""
	existing = frappe.db.get_value(
		"Cloud Usage Anomaly",
		{
			"account": anomaly["account"],
			"series_key": anomaly["series_key"],
			"detector": anomaly["detector"],
			"status": ("in", ["Open", "Acknowledged"]),
		},
		["name", "changed_on"],
		as_dict=True,
	)

	if not existing and is_dismissed(anomaly):
		return None

	contributors = get_contributors(anomaly["usage_type"], anomaly["region"], anomaly["changed_on"])

	if existing:
		doc = frappe.get_doc("Cloud Usage Anomaly", existing.name)
		doc.update(anomaly)
	else:
		doc = frappe.get_doc({"doctype": "Cloud Usage Anomaly", **anomaly})

	doc.contributors = []
	for contributor in contributors:
		doc.append("contributors", contributor)
	doc.save(ignore_permissions=True)

	if not existing:
		notify(doc)
	if anomaly["detector"] == "Level Shift":
		supersede_spikes(anomaly)
	return doc


def supersede_spikes(anomaly):
	"""Once a series is understood as a new level, the spike filed while it was still
	just a loud day is answered. Leaving it open makes the queue count one event twice."""
	spikes = frappe.get_all(
		"Cloud Usage Anomaly",
		{
			"account": anomaly["account"],
			"series_key": anomaly["series_key"],
			"detector": "Spike",
			"status": ("in", ["Open", "Acknowledged"]),
		},
		pluck="name",
	)
	for name in spikes:
		frappe.db.set_value("Cloud Usage Anomaly", name, "status", "Resolved")


def notify(anomaly):
	"""Only unexplained growth is worth interrupting someone for. Growth its driver
	kept pace with is recorded and left in the list."""
	if anomaly.verdict != "Inorganic":
		return

	contributors = "\n".join(
		f"- {row.label}: {row.value:,.1f} {row.unit or ''}".rstrip() for row in anomaly.contributors
	)
	message = f"*Unexplained cloud usage*\n\n{anomaly.summary}"
	if contributors:
		message += f"\n\nLargest contributors:\n{contributors}"

	TelegramMessage.enqueue(message=message, topic="Cloud Cost", priority="Medium")


def is_dismissed(anomaly):
	"""An operator who resolved or dismissed this exact finding should not see it again."""
	return bool(
		frappe.db.exists(
			"Cloud Usage Anomaly",
			{
				"account": anomaly["account"],
				"series_key": anomaly["series_key"],
				"detector": anomaly["detector"],
				"changed_on": anomaly["changed_on"],
				"status": ("in", ["Resolved", "False Positive"]),
			},
		)
	)


def detect_anomalies():
	settings = frappe.get_single("Cloud Cost Settings")
	# Yesterday is the last complete day AWS has billed. The window is inclusive of both
	# ends, so it holds exactly as many days as the setting asks for.
	end = add_days(getdate(), -1)
	start = add_days(end, -((cint(settings.baseline_days) or 28) - 1))

	drivers = get_driver_series(start, end)
	found = 0
	for (account, key), rows in get_cost_series(start, end).items():
		anomaly = build_anomaly(account, key, rows, settings, drivers, start, end)
		if anomaly and save_anomaly(anomaly):
			found += 1

	frappe.db.commit()
	return found


def run_daily_pipeline():
	"""Ingest, then count what the business did, then compare the two. Ordering matters
	enough to keep it in one job rather than three scheduler entries."""
	from press.press.doctype.cloud_cost_daily.cloud_cost_daily import (
		ingest_daily_costs,
		purge_old_rows,
	)
	from press.press.doctype.cloud_usage_driver.cloud_usage_driver import collect_daily_drivers

	if not frappe.db.get_single_value("Cloud Cost Settings", "enabled"):
		return

	ingest_daily_costs()
	collect_daily_drivers()
	detect_anomalies()
	purge_old_rows()
