from frappe import frappe

from press.utils import get_current_team

SUPPORT_AGENT_ACCESS = {
	"Site": {
		"Apps": False,
		"Domains": False,
		"Backups": False,
		"Site Config": False,
		"Actions": False,
		"Activity": False,
	}
}


def add_tabs_access(doc: frappe._dict):
	if hasattr(doc, "team") and doc.team == get_current_team():
		return doc
	if config := SUPPORT_AGENT_ACCESS.get(doc.doctype):
		doc.tabs_access = config
	return doc
