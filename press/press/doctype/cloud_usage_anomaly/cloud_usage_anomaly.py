# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate

from press.press.doctype.cloud_cost_daily.adapters import ACCRUED
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

# The shape of detection is a design decision, not an operations one. These are the
# numbers to argue about in a pull request, not knobs to leave on a settings page for
# nobody to turn. Only the money floors, which decide how much a change has to be worth
# before anyone hears about it, are configurable.
BASELINE_DAYS = 30
SPIKE_MAD_THRESHOLD = 3
LEVEL_SHIFT_MINIMUM_CHANGE = 20
ORGANIC_TOLERANCE = 5

# What each kind of usage is expected to grow with, per provider, because the four of
# them name things nothing alike: AWS folds storage and snapshots into usage types under
# EC2-Other, OCI answers with a service and a SKU, and the two accrued providers use the
# names our own adapters give them. Ordered: the first rule that matches wins, so the
# specific ones come before the general ones.
DRIVER_RULES = {
	"AWS EC2": [
		("usage_type", "EBS:SnapshotUsage", DRIVER_SNAPSHOT_SIZE),
		("usage_type", "EBS:VolumeUsage", DRIVER_VOLUME_SIZE),
		("usage_type", "EBS:VolumeP-IOPS", DRIVER_VOLUME_SIZE),
		("usage_type", "BoxUsage", DRIVER_RUNNING_MACHINES),
		("usage_type", "SpotUsage", DRIVER_RUNNING_MACHINES),
		("usage_type", "DedicatedUsage", DRIVER_RUNNING_MACHINES),
		("usage_type", "TimedStorage", DRIVER_BACKUP_STORED),
		("usage_type", "Requests-Tier", DRIVER_BACKUP_OBJECTS),
		("usage_type", "DataTransfer", DRIVER_ACTIVE_SITES),
		("usage_type", "NatGateway", DRIVER_ACTIVE_SITES),
	],
	"OCI": [
		# Volume backups bill under the block storage service, so the SKU has to be read
		# before the service or every snapshot leak reads as a volume growing.
		("usage_type", "Backup", DRIVER_SNAPSHOT_SIZE),
		("service", "BLOCK_STORAGE", DRIVER_VOLUME_SIZE),
		("service", "COMPUTE", DRIVER_RUNNING_MACHINES),
		("service", "OBJECT_STORAGE", DRIVER_BACKUP_STORED),
	],
	"Hetzner": [
		("usage_type", "Server:", DRIVER_RUNNING_MACHINES),
		("usage_type", "Volume", DRIVER_VOLUME_SIZE),
		("usage_type", "Snapshot", DRIVER_SNAPSHOT_SIZE),
		("usage_type", "Traffic", DRIVER_ACTIVE_SITES),
	],
	"DigitalOcean": [
		("usage_type", "Droplet:", DRIVER_RUNNING_MACHINES),
		("usage_type", "Volume", DRIVER_VOLUME_SIZE),
		("usage_type", "Snapshot", DRIVER_SNAPSHOT_SIZE),
	],
}


class CloudUsageAnomaly(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Data | None
		baseline_value: DF.Float
		change_percent: DF.Percent
		changed_on: DF.Date | None
		contributors: DF.TextEditor | None
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


def driver_for(provider, service, usage_type):
	values = {"service": service or "", "usage_type": usage_type or ""}
	for field, marker, driver in DRIVER_RULES.get(provider, []):
		if marker in values[field]:
			return driver
	return None


def get_cost_series(start, end):
	"""Every day's cost and usage, grouped into one series per account, service, usage
	type and region."""
	rows = frappe.get_all(
		"Cloud Cost Daily",
		{"date": ("between", [start, end])},
		[
			"date",
			"account",
			"provider",
			"source",
			"currency",
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
		["date", "driver", "provider", "value"],
		order_by="date asc",
		limit_page_length=0,
	)

	series = {}
	for row in rows:
		key = (row.driver, row.provider or "")
		series.setdefault(key, []).append({"date": getdate(row.date), "value": flt(row.value)})
	return series


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
	found = detect_level_shift(points, LEVEL_SHIFT_MINIMUM_CHANGE)
	detector = "Level Shift"
	if not found:
		found = detect_spike(points, SPIKE_MAD_THRESHOLD)
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
		"provider": sample.provider,
		"currency": sample.currency,
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
	anomaly.update(judge(sample, drivers, found))
	anomaly["summary"] = describe(anomaly)
	return anomaly


def judge(sample, drivers, found):
	"""Growth that its driver kept up with is the product working. Growth its driver
	did not follow is the alert.

	The provider's own count is preferred over the fleet's: Hetzner volumes growing says
	nothing about whether AWS storage should have grown, and judging one against the
	other would call a real leak organic.
	"""
	driver = driver_for(sample.provider, sample.service, sample.usage_type)
	if not driver:
		return {"driver": None, "driver_change_percent": 0, "verdict": "No Driver"}

	points = drivers.get((driver, sample.provider)) or drivers.get((driver, ""))
	if not points:
		return {"driver": driver, "driver_change_percent": 0, "verdict": "No Driver"}

	movement = split_mean_change(points, found["changed_on"])
	if not movement:
		return {"driver": driver, "driver_change_percent": 0, "verdict": "No Driver"}

	driver_percent = change_percent(movement["baseline"], movement["current"])
	organic = driver_percent >= found["change_percent"] - ORGANIC_TOLERANCE

	return {
		"driver": driver,
		"driver_change_percent": driver_percent,
		"verdict": "Organic" if organic else "Inorganic",
	}


def describe(anomaly):
	movement = "stepped" if anomaly["detector"] == "Level Shift" else "spiked"
	what_moved = (
		f"{anomaly['series_key']} {movement} from {anomaly['baseline_value']:,.2f}"
		f" to {anomaly['current_value']:,.2f} {anomaly['unit']} on {anomaly['changed_on']}"
		f" ({anomaly['change_percent']:+.1f}%)."
	)
	what_it_costs = (
		f"Costing about {anomaly['daily_cost_impact']:,.2f} {anomaly['currency']} a day more"
		f" ({anomaly['monthly_cost_impact']:,.0f} a month)."
	)
	if anomaly["verdict"] == "No Driver":
		why = "No business driver is mapped to this usage type, so it cannot be explained away."
	else:
		why = (
			f"{anomaly['driver']} moved {anomaly['driver_change_percent']:+.1f}% over the same days,"
			f" so this reads as {anomaly['verdict'].lower()}."
		)
	return "\n".join([what_moved, what_it_costs, why])


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

	contributors = get_contributors(
		anomaly["provider"], anomaly["usage_type"], anomaly["region"], anomaly["changed_on"]
	)

	anomaly["contributors"] = render_contributors(contributors)
	if existing:
		doc = frappe.get_doc("Cloud Usage Anomaly", existing.name)
		doc.update(anomaly)
	else:
		doc = frappe.get_doc({"doctype": "Cloud Usage Anomaly", **anomaly})

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


def render_contributors(contributors):
	"""Contributors are read, never queried, so they are rendered once here instead of
	earning a child table of their own. The links still open the record."""
	items = []
	for row in contributors:
		route = f"/app/{frappe.scrub(row['document_type']).replace('_', '-')}/{row['document_name']}"
		value = f"{row['value']:,.1f} {row['unit']}".rstrip()
		items.append(f"<li><a href='{route}'>{frappe.utils.escape_html(row['label'])}</a> — {value}</li>")
	return f"<ul>{''.join(items)}</ul>" if items else ""


def notify(anomaly):
	"""Only unexplained growth is worth interrupting someone for. Growth its driver kept
	pace with is recorded and left in the list.

	No Driver counts as unexplained. A usage type nothing in Press drives is the case we
	understand least, and staying quiet about it would make an unmapped series the
	safest place for a leak to hide.
	"""
	if anomaly.verdict == "Organic":
		return

	TelegramMessage.enqueue(
		message=f"*Unexplained cloud usage*\n\n{anomaly.summary}",
		topic="Cloud Cost",
		priority="Medium",
	)


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


def last_complete_day(rows, today):
	"""The last day this account has whole data for.

	An accrued source prices today's inventory the moment it runs, so today is already
	complete and waiting for tomorrow would delay the alert by a day on exactly the
	providers where the reading is live. A metered provider is still billing today, so
	yesterday is the last day worth judging.
	"""
	if all(row.source == ACCRUED for row in rows):
		return today
	return add_days(today, -1)


def get_stale_accounts(series, today):
	"""Accounts whose most recent day never arrived.

	Ingest isolates each account so one bad token does not discard three healthy
	providers, which means a single account can be left short of today while the rest
	are current. Its series then end in a gap, gaps are read as zeros, and a run of
	trailing zeros makes a real problem look like calm. Not judging is the honest
	answer, and saying so out loud is the point.
	"""
	latest = {}
	expected = {}
	for (account, _key), rows in series.items():
		expected[account] = last_complete_day(rows, today)
		newest = max(getdate(row.date) for row in rows)
		latest[account] = max(latest.get(account, newest), newest)

	stale = {account for account, day in expected.items() if latest[account] < day}
	if stale:
		frappe.log_error(
			title="Cloud Cost Detection Skipped Stale Accounts",
			message="No data for the latest complete day: " + ", ".join(sorted(stale)),
		)
	return stale


def detect_anomalies():
	settings = frappe.get_single("Cloud Cost Settings")
	today = getdate()

	# Widest window any source could need, narrowed per series once its own last
	# complete day is known.
	drivers = get_driver_series(add_days(today, -BASELINE_DAYS), today)
	series = get_cost_series(add_days(today, -BASELINE_DAYS), today)
	stale = get_stale_accounts(series, today)

	found = 0
	for (account, key), rows in series.items():
		if account in stale:
			continue

		end = last_complete_day(rows, today)
		start = add_days(end, -(BASELINE_DAYS - 1))
		window = [row for row in rows if start <= getdate(row.date) <= end]
		if not window:
			continue

		anomaly = build_anomaly(account, key, window, settings, drivers, start, end)
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
