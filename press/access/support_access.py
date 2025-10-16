import frappe
import frappe.utils

from press.access.actions import SiteActions
from press.utils import get_current_team

TAB_DF_MAP = {
	"Site": {
		"Domains": "site_domains",
	},
}

ACTION_DF_MAP = {
	"Site": {
		SiteActions.LOGIN_AS_ADMINISTRATOR: "login_as_administrator",
	}
}


def get_extra_field(doctype: str, perm: str | None) -> str | None:
	if not perm:
		return None
	if field := TAB_DF_MAP.get(doctype, {}).get(perm):
		return field
	if field := ACTION_DF_MAP.get(doctype, {}).get(perm):
		return field
	return None


def has_support_access(doctype: str, docname: str, action: str | None = None) -> bool:
	"""
	Checks if current team has support access to given document.
	"""

	if frappe.local.system_user():
		return True

	filters = {
		"status": "Accepted",
		"requested_team": get_current_team(),
		"access_allowed_till": (">", frappe.utils.now_datetime()),
	}

	if field := get_extra_field(doctype, action):
		filters[field] = 1

	accesses = frappe.get_all("Support Access", filters=filters, pluck="name")

	for access in accesses:
		if frappe.db.exists(
			"Support Access Resource",
			{
				"parent": access,
				"document_type": doctype,
				"document_name": docname,
			},
		):
			return True

	return False
