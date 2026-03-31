import frappe

from press.access.support_access import ACTION_DF_MAP, TAB_DF_MAP, has_support_access
from press.utils import get_current_team

from .actions import ACTIONS_RULES
from .tabs import TABS_RULES

SECTIONS = {
	"actions_access": ACTIONS_RULES,
	"tabs_access": TABS_RULES,
}


def dashboard_access_rules(data: frappe._dict):
	"""
	Apply access rules to the dashboard data based on the current team.
	"""

	data.tabs_access = {}
	data.actions_access = {}

	if frappe.local.system_user():
		return data

	if hasattr(data, "team") and data.team == get_current_team():
		return data

	# Casting to string to avoid issues with `None`
	doctype, docname = str(data.doctype), str(data.name)

	actions = ACTIONS_RULES.get(doctype, {})
	actions_maps = ACTION_DF_MAP.get(doctype, {})
	for rule, value in actions.items():
		data.actions_access[rule] = value
		if rule in actions_maps:
			data.actions_access[rule] = has_support_access(doctype, docname, rule)

	tabs = TABS_RULES.get(doctype, {})
	tabs_maps = TAB_DF_MAP.get(doctype, {})
	for rule, value in tabs.items():
		data.tabs_access[rule] = value
		if rule in tabs_maps:
			data.tabs_access[rule] = has_support_access(doctype, docname, rule)

	return data
