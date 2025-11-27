import frappe
import frappe.utils
from frappe import _
from frappe.utils import caching, typing_validations

from press.access import support_access


@frappe.whitelist()
@caching.redis_cache(ttl=60, user=True)
@typing_validations.validate_argument_types
def status(doctype: str, docname: str):
	if not support_access.has_support_access(doctype, docname):
		message = _("You do not have support access to this document.")
		frappe.throw(message, frappe.PermissionError)

	AccessRequest = frappe.qb.DocType("Support Access")
	AccessRequestResource = frappe.qb.DocType("Support Access Resource")

	query = (
		frappe.qb.from_(AccessRequest)
		.inner_join(AccessRequestResource)
		.on(AccessRequest.name == AccessRequestResource.parent)
		.select(AccessRequest.star)
		.where(AccessRequest.status == "Accepted")
		.where(AccessRequestResource.document_type == doctype)
		.where(AccessRequestResource.document_name == docname)
		.where(AccessRequest.access_allowed_till > frappe.utils.now_datetime())
		.orderby(AccessRequest.access_allowed_till, order=frappe.qb.desc)
	)

	results = query.run(as_dict=True)

	if len(results) == 0:
		message = _("You do not have support access to this document.")
		frappe.throw(message, frappe.PermissionError)

	until = results[0].access_allowed_till

	def map_permission(permission: str) -> dict:
		label = frappe.get_meta("Support Access").get_field(permission).get("label")
		applicable = list(filter(lambda x: bool(x[permission]), results))
		longest = max(applicable, key=lambda x: x.access_allowed_till) if applicable else None
		return {
			"name": label,
			"allowed": bool(longest),
			"until": longest.access_allowed_till if longest else None,
		}

	def get_permissions() -> list[str]:
		match doctype:
			case "Site":
				return ["site_domains", "login_as_administrator", "site_release_group", "bench_ssh"]
			case "Release Group":
				return ["bench_ssh"]
			case _:
				return []

	permissions = [map_permission(permission) for permission in get_permissions()]

	return {
		"until": until,
		"permissions": permissions,
	}
