from frappe import frappe

from press.utils import get_current_team

SUPPORT_AGENT_ACCESS = {
	"Site": {
		"Visit Site": True,
		"View in Desk": False,
		"Login As Administrator": False,
	}
}


def add_actions_access(doc: frappe._dict):
	if hasattr(doc, "team") and doc.team == get_current_team():
		return doc
	if config := SUPPORT_AGENT_ACCESS.get(doc.doctype):
		doc.actions_access = config
	return doc
