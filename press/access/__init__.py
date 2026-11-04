import frappe

from press.access.support_access import is_insider, outsider_can_access

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

	if is_insider(data.get("team")):
		return data

	# Casting to string to avoid issues with `None`
	doctype, docname = str(data.doctype), str(data.name)

	data.actions_access = {
		rule: outsider_can_access(doctype, docname, rule, allowed)
		for rule, allowed in ACTIONS_RULES.get(doctype, {}).items()
	}
	data.tabs_access = {
		rule: outsider_can_access(doctype, docname, rule, allowed)
		for rule, allowed in TABS_RULES.get(doctype, {}).items()
	}

	return data
