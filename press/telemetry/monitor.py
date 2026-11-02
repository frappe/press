from contextlib import suppress

import frappe
from frappe.monitor import add_data_to_monitor

from press.utils import get_current_team


def add_user_context(**kwargs):
	with suppress(Exception):
		add_data_to_monitor(user_details=get_user_details())


def get_user_details() -> dict:
	return {
		"user": frappe.session.user,
		"team": get_current_team(get_doc=False) if frappe.session.user != "Guest" else None,
	}
