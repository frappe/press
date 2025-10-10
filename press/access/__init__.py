import frappe

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
	if hasattr(data, "team") and data.team == get_current_team():
		return data
	for section, rules in SECTIONS.items():
		if config := rules.get(data.doctype):
			setattr(data, section, config)
	return data
