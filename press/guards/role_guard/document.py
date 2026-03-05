import frappe
from frappe.query_builder import Not
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder

from press.utils import get_current_team


def check(base_query: QueryBuilder, document_type: str, document_name: str | None = None) -> bool | list[str]:
	if document_name:
		return has_user_permission(document_type) or document(base_query, document_type, document_name)
	if has_user_permission(document_type):
		return []
	return documents(base_query, document_type)


def documents(base_query: QueryBuilder, document_type: str) -> list[str]:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	return [
		doc.document_name
		for doc in base_query.inner_join(PressRoleResource)
		.on(
			(PressRoleResource.parent == PressRole.name)
			& (PressRoleResource.document_type == document_type)
			& (Not(PressRoleResource.document_name.isnull()))
		)
		.select(PressRoleResource.document_name)
		.distinct()
		.run(as_dict=True)
	]


def document(base_query: QueryBuilder, document_type: str, document_name: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleResource = frappe.qb.DocType("Press Role Resource")
	return (
		base_query.inner_join(PressRoleResource)
		.on(
			(PressRoleResource.parent == PressRole.name)
			& (PressRoleResource.document_type == document_type)
			& (PressRoleResource.document_name == document_name)
		)
		.select(Count(PressRole.name).as_("document_count"))
		.run(as_dict=True)
		.pop()
		.get("document_count")
		> 0
	)


def has_user_permission(doctype: str) -> bool:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	# HACK: This is probably not a good idea. At this point, only possible
	# doctypes are servers, sites and release groups.
	key = f"all_{doctype.replace(' ', '_').lower()}s"
	return (
		frappe.qb.from_(PressRole)
		.inner_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRole.team == get_current_team())
		.where(PressRole[key] == 1)
		.where(PressRoleUser.user == frappe.session.user)
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)
