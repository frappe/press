# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.utils import now_datetime
from press.utils import log_error
from frappe.utils import nowtime, get_time, get_datetime


def trigger():
	"""Will be triggered every 30 minutes"""
	# Get all ["Active", "Inactive"] sites
	# Trigger "Daily" frequency sites
	sites_with_daily_scheduled_updates = frappe.get_all(
		"Site",
		filters={"status": ("in", ("Active", "Inactive")), "auto_updates_scheduled": True},
		fields=[
			"name",
			"auto_update_last_triggered_on",
			"update_trigger_time",
			"update_trigger_frequency",
		],
	)

	trigger_for_sites = list(
		filter(sites_with_daily_scheduled_updates, should_update_trigger)
	)

	for site in trigger_for_sites:
		try:
			site_doc = frappe.get_doc("Site", site.name)
			site_doc.schedule_update()
			site_doc.auto_update_last_triggered_on = now_datetime()
			site_doc.save()
		except Exception:
			traceback = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			log_error("Scheduled Auto Update Failed", site=site, traceback=traceback)


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
	if doc.auto_update_last_triggered_on.date() == current_datetime.date() and get_time(doc.update_trigger_time) <= get_time(doc.auto_update_last_triggered_on):
		return False
	elif get_time(doc.update_trigger_time) <= get_time(current_datetime):
		return True

def should_update_trigger_for_weekly(site, current_datetime=get_datetime()):
	"""Takes `current_datetime` to make testing easier."""
	pass


def should_update_trigger_for_monthly(site, current_datetime=get_datetime()):
	"""Takes `current_datetime` to make testing easier."""
	pass