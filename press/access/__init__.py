import frappe

from press.access.support_access import ACTION_DF_MAP, has_support_access
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
			for rule in ACTION_DF_MAP.get(data.doctype, {}):
				if rule in config:
					config[rule] = has_support_access(data.doctype, data.name, rule)
			setattr(data, section, config)

	return data
