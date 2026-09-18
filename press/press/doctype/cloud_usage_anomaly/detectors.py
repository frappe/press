# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Change detection over a daily series.

Two detectors, because they see different things. A spike is one loud day against its
own weekday history. A level shift is a series that quietly settled at a new number and
stayed there — the shape behind a bill that is thirty percent higher than last month
without any single day ever looking wrong.

Everything here takes and returns plain values so it can be tested without a database.
"""

MINIMUM_SEGMENT_DAYS = 3
MINIMUM_BASELINE_POINTS = 3
# A perfectly flat series has no deviation to measure against, so a relative change is
# the only honest test left.
FLAT_SERIES_CHANGE_PERCENT = 20


def median(values):
	if not values:
		return 0

	ordered = sorted(values)
	middle = len(ordered) // 2
	if len(ordered) % 2:
		return ordered[middle]
	return (ordered[middle - 1] + ordered[middle]) / 2


def median_absolute_deviation(values, center):
	if not values:
		return 0
	return median([abs(value - center) for value in values])


def mean(values):
	return sum(values) / len(values) if values else 0


def change_percent(baseline, current):
	if not baseline:
		return 100.0 if current else 0.0
	return (current - baseline) / abs(baseline) * 100


def detect_spike(series, mad_threshold):
	"""One day standing well clear of the same weekday's history.

	Weekday matters: backups, deploys and business traffic all run on a weekly shape,
	and comparing a Sunday against a week of weekdays produces an alert every Sunday.
	"""
	if len(series) < MINIMUM_BASELINE_POINTS + 1:
		return None

	*history, latest = series
	weekday = latest["date"].weekday()
	baseline_points = [point["value"] for point in history if point["date"].weekday() == weekday]
	if len(baseline_points) < MINIMUM_BASELINE_POINTS:
		baseline_points = [point["value"] for point in history]

	center = median(baseline_points)
	if latest["value"] <= center:
		return None

	deviation = median_absolute_deviation(baseline_points, center)
	if deviation:
		if (latest["value"] - center) / deviation < mad_threshold:
			return None
	elif change_percent(center, latest["value"]) < FLAT_SERIES_CHANGE_PERCENT:
		return None

	return {
		"changed_on": latest["date"],
		"baseline": center,
		"current": latest["value"],
		"change_percent": change_percent(center, latest["value"]),
	}


def detect_level_shift(series, minimum_change_percent):
	"""The day a series stopped being one number and started being another.

	Every day is tried as the boundary and the one that splits the series most cleanly
	wins, weighted so a split with days on both sides beats a split that just clips the
	tail. The boundary is located on means, which move the moment the series does and so
	land on the right day; the two levels are then reported as medians, which one loud
	day cannot drag, so a single outlier is left to the spike detector where it belongs.

	This runs before the spike detector. A series that settled at a new number three
	weeks ago should report the day it settled, not report today.
	"""
	if len(series) < MINIMUM_SEGMENT_DAYS * 2:
		return None

	values = [point["value"] for point in series]
	total = len(values)

	best = None
	for index in range(MINIMUM_SEGMENT_DAYS, total - MINIMUM_SEGMENT_DAYS + 1):
		before, after = values[:index], values[index:]
		separation = abs(mean(after) - mean(before)) * (len(before) * len(after) / total) ** 0.5
		if not best or separation > best["separation"]:
			best = {"separation": separation, "index": index, "before": before, "after": after}

	baseline, current = median(best["before"]), median(best["after"])
	if current <= baseline:
		return None

	shift = change_percent(baseline, current)
	if shift < minimum_change_percent:
		return None

	return {
		"changed_on": series[best["index"]]["date"],
		"baseline": baseline,
		"current": current,
		"change_percent": shift,
	}
