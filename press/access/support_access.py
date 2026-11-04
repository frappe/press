import frappe
import frappe.utils
from frappe.utils import cstr

from press import utils as press_utils
from press.access import utils as access_utils
from press.access.actions import ACTIONS_RULES, ReleaseGroupActions, SiteActions

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


def is_insider(team: str | None) -> bool:
	"""
	A member employee (by membership, as desk sends no team), or a customer
	acting for `team`. System Managers, Administrator among them, always count.
	"""
	if press_utils._system_user():
		return not access_utils.is_outside_employee(team)
	return bool(team) and team == press_utils.get_current_team()


def can_perform(doctype: str, docname: str, team: str | None, action: str) -> bool:
	"""Whether the session may use `action` on `docname`, a document of `team`."""
	if is_insider(team):
		return True
	allowed = ACTIONS_RULES.get(doctype, {}).get(action, True)
	return outsider_can_access(doctype, docname, action, allowed)


def outsider_can_access(doctype: str, docname: str, rule: str, allowed: bool) -> bool:
	"""Whether a support agent or an employee may use the action or tab `rule`."""
	if get_extra_field(doctype, rule):
		return allowed or has_grant(doctype, docname, rule)
	# Employees need consent only for the rules a grant names.
	return allowed or press_utils._system_user()


def has_support_access(doctype: str, docname: str) -> bool:
	"""
	Checks if current team has support access to given document.
	"""
	return press_utils._system_user() or has_grant(doctype, docname, None)


def has_grant(doctype: str, docname: str, rule: str | None) -> bool:
	"""Whether an accepted Support Access lets an employee or support agent use `rule`."""
	if not (press_utils._system_user() or press_utils.has_role("Press Support Agent")):
		return False

	return any(
		is_granted(covering_doctype, covering_name, rule)
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
