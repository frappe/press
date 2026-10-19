import frappe
import frappe.utils
from frappe.utils import cstr

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


# A grant covers a document when it covers any document that the document links to.
COVERING_LINKS = {
	"Agent Job": (("site", "Site"), ("bench", "Bench")),
	"Bench": (("group", "Release Group"),),
	"Deploy Candidate": (("group", "Release Group"),),
	"Deploy Candidate Build": (("group", "Release Group"),),
	"Release Pipeline": (("release_group", "Release Group"),),
}


def resources_covering(doctype: str, docname: str) -> list[tuple[str, str]]:
	"""The documents a grant can name to cover `docname`."""
	if not docname:
		return []
	if doctype not in COVERING_LINKS:
		return [(doctype, docname)]
	return [
		resource
		for covering in covering_links_of(doctype, docname)
		for resource in resources_covering(*covering)
	]


def covering_links_of(doctype: str, docname: str) -> list[tuple[str, str]]:
	return [
		(covering_doctype, cstr(frappe.db.get_value(doctype, docname, link_field)))
		for link_field, covering_doctype in COVERING_LINKS[doctype]
	]


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

	return any(
		is_granted(covering_doctype, covering_name, action)
		for covering_doctype, covering_name in resources_covering(doctype, docname)
	)


def is_granted(doctype: str, docname: str, action: str | None) -> bool:
	if access_utils.is_public_resource(doctype, docname):
		return True

	filters: dict[str, object] = {
		"status": "Accepted",
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
