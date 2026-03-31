import frappe
import frappe.utils

from press import utils as press_utils
from press.access import utils as access_utils
from press.access.actions import ReleaseGroupActions, SiteActions

TAB_DF_MAP = {
	"Site": {
		"Domains": "site_domains",
	},
}

ACTION_DF_MAP = {
	"Release Group": {
		ReleaseGroupActions.SSHAccess.value: "bench_ssh",
	},
	"Site": {
		SiteActions.LoginAsAdmin.value: "login_as_administrator",
	},
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

	if not press_utils.has_role("Press Support Agent"):
		return False

	if access_utils.is_public_resource(doctype, docname):
		return True

	filters = {
		"status": "Accepted",
		"access_allowed_till": (">", frappe.utils.now_datetime()),
	}

	if field := get_extra_field(doctype, action):
		filters[field] = 1

	accesses = frappe.get_all("Support Access", filters=filters, pluck="name")

	if doctype == "Bench":
		doctype = "Release Group"
		docname = frappe.get_value("Bench", docname, "group")

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
