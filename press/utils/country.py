# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import functools

import frappe


@functools.cache
def get_frappe_country_data_by_code() -> dict[str, dict]:
	"""Frappe's bundled country data, keyed by ISO code instead of country name."""
	from frappe.geo.country_info import get_all as get_country_data

	return {info["code"].lower(): info for info in get_country_data().values() if info.get("code")}


def get_isd_code(code: str | None) -> str:
	"""ISD code for an ISO country code, from frappe's bundled data."""
	return get_frappe_country_data_by_code().get((code or "").lower(), {}).get("isd", "")


def get_country_timezones(country: str) -> list[str]:
	"""Timezones for a country, from our `Country` doctype."""
	code, time_zones = frappe.db.get_value("Country", country, ["code", "time_zones"]) or (None, None)
	if time_zones:
		return time_zones.splitlines()

	return get_frappe_country_data_by_code().get((code or "").lower(), {}).get("timezones") or []
