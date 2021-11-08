# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from calendar import monthrange
from press.utils import log_error
from frappe.utils import now_datetime
from frappe.utils import get_time, get_datetime
from press.press.doctype.site_update.site_update import benches_with_available_update


def trigger():
	"""Will be triggered every 30 minutes"""
	# Get all ["Active", "Inactive"] sites
	# with auto updates scheduled
	sites_with_scheduled_updates = frappe.get_all(
		"Site",
		filters={
			"status": ("in", ("Active", "Inactive")),
			"auto_updates_scheduled": True,
			"bench": (
				"in",
				benches_with_available_update(),  # An update should be available for this site
			),
		},
		fields=[
			"name",
			"auto_update_last_triggered_on",
			"update_trigger_time",
			"update_trigger_frequency",
			"update_on_weekday",
			"update_end_of_month",
			"update_on_day_of_month",
		],
	)

	trigger_for_sites = list(filter(should_update_trigger, sites_with_scheduled_updates))

	for site in trigger_for_sites:
		auto_update_log = frappe.get_doc(
			{
				"doctype": "Scheduled Auto Update Log",
				"document_type": "Site",
				"document_name": site.name,
				"status": "Success",
			}
		)

		# Set the frequency details in log
		set_schedule_details(auto_update_log, site)

		try:
			site_doc = frappe.get_doc("Site", site.name)
			site_doc.schedule_update()
			site_doc.auto_update_last_triggered_on = now_datetime()
			site_doc.save()
		except Exception:
			traceback = "<pre><code>" + frappe.get_traceback() + "</pre></code>"

			# Update log doc
			auto_update_log.status = "Failed"
			auto_update_log.error = traceback

			log_error("Scheduled Auto Update Failed", site=site, traceback=traceback)
		finally:
			auto_update_log.insert(ignore_permissions=True)


def should_update_trigger(doc):
	"""
	Returns `True` if the doc update should be triggered.
	"""
	# Return based on the set frequency
	if doc.update_trigger_frequency == "Daily":
		return should_update_trigger_for_daily(doc)
	elif doc.update_trigger_frequency == "Weekly":
		return should_update_trigger_for_weekly(doc)
	elif doc.update_trigger_frequency == "Monthly":
		return should_update_trigger_for_monthly(doc)

	return False


def should_update_trigger_for_daily(doc, current_datetime=get_datetime()):
	"""Takes `current_datetime` to make testing easier."""
	auto_update_last_triggered_on = doc.auto_update_last_triggered_on

	if (
		auto_update_last_triggered_on
		and auto_update_last_triggered_on.date() == current_datetime.date()
		and get_time(doc.update_trigger_time) <= get_time(auto_update_last_triggered_on)
	):
		return False
	elif get_time(doc.update_trigger_time) <= get_time(current_datetime):
		return True

	return False


def should_update_trigger_for_weekly(doc, current_datetime=get_datetime()):
	"""Takes `current_datetime` to make testing easier."""
	if doc.update_on_weekday != current_datetime.strftime("%A"):
		return False

	auto_update_last_triggered_on = doc.auto_update_last_triggered_on

	# Today is `update_on_weekday`
	if (
		auto_update_last_triggered_on
		and auto_update_last_triggered_on.date() == current_datetime.date()
		and get_time(doc.update_trigger_time) <= get_time(auto_update_last_triggered_on)
	):
		return False

	if get_time(doc.update_trigger_time) <= get_time(current_datetime):
		return True

	return False


def should_update_trigger_for_monthly(doc, current_datetime=get_datetime()):
	"""Takes `current_datetime` to make testing easier."""
	if doc.update_end_of_month:
		on_day_of_month = get_last_day_of_month(current_datetime.year, current_datetime.month)
	else:
		on_day_of_month = doc.update_on_day_of_month

	if on_day_of_month != current_datetime.day:
		return False

	auto_update_last_triggered_on = doc.auto_update_last_triggered_on

	if (
		auto_update_last_triggered_on
		and auto_update_last_triggered_on.date() == current_datetime.date()
		and get_time(doc.update_trigger_time) <= get_time(auto_update_last_triggered_on)
	):
		return False

	if get_time(doc.update_trigger_time) <= get_time(current_datetime):
		return True

	return False


def get_last_day_of_month(year, month):
	return monthrange(year, month)[1]


def set_schedule_details(update_log_doc, doc):
	update_log_doc.was_scheduled_for_frequency = doc.update_trigger_frequency
	update_log_doc.was_scheduled_for_time = doc.update_trigger_time

	if doc.update_trigger_frequency == "Weekly":
		update_log_doc.was_scheduled_for_day = doc.update_on_weekday
	elif doc.update_trigger_frequency == "Monthly":
		update_log_doc.was_scheduled_for_month_day = str(doc.update_on_day_of_month)
		update_log_doc.was_scheduled_for_month_end = doc.update_end_of_month
