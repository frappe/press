from typing import TypedDict, cast

import frappe
import frappe.utils
from frappe.types.DF import Data
from pypika import Not
from pypika import functions as fn
from pypika.terms import ValueWrapper

PERMISSION_FIELDS = [
	"admin_access",
	"allow_apps",
	"allow_bench_creation",
	"allow_billing",
	"allow_contribution",
	"allow_customer",
	"allow_dashboard",
	"allow_leads",
	"allow_partner",
	"allow_server_creation",
	"allow_site_creation",
	"allow_webhook_configuration",
	"all_release_groups",
	"all_servers",
	"all_sites",
]


def get_invitations(team: str):
	AccountRequest = frappe.qb.DocType("Account Request")
	PressRole = frappe.qb.DocType("Press Role")
	User = frappe.qb.DocType("User")
	return (
		frappe.qb.from_(AccountRequest)
		.left_join(User)
		.on(AccountRequest.email == User.email)
		.left_join(PressRole)
		.on(AccountRequest.press_role == PressRole.name)
		.where(AccountRequest.team == team)
		.where(Not(AccountRequest.invited_by.isnull()))
		.where(AccountRequest.request_key_expiration_time > frappe.utils.now_datetime())
		# Acceptance nulls request_key and the expiry scheduler blanks it, both
		# without touching the expiration time, so the key must be checked too.
		.where(Not(AccountRequest.request_key.isnull()))
		.where(AccountRequest.request_key != "")
		.select(
			AccountRequest.name,
			AccountRequest.email,
			AccountRequest.request_key_expiration_time.as_("date"),
			fn.Coalesce(PressRole.title, AccountRequest.press_role).as_("press_role"),
			PressRole.name.as_("press_role_name"),
			PressRole.admin_access.as_("press_role_admin_access"),
			ValueWrapper("Pending").as_("status"),
			User.full_name,
			User.user_image,
		)
		.run(as_dict=True)
	)


class RoleDict(TypedDict):
	label: str
	value: str
	name: str
	admin_access: bool
	allow_apps: bool
	allow_bench_creation: bool
	allow_billing: bool
	allow_contribution: bool
	allow_customer: bool
	allow_dashboard: bool
	allow_leads: bool
	allow_partner: bool
	allow_server_creation: bool
	allow_site_creation: bool
	allow_webhook_configuration: bool
	all_release_groups: bool
	all_servers: bool
	all_sites: bool


def get_roles(team: Data | None) -> list[RoleDict]:
	"""
	Get the custom Press Roles defined for the given team. Returns an empty list
	when no team is provided or when the team has no Press Roles.

	Each role includes its full permission configuration.
	"""
	if not team:
		return []

	PressRole = frappe.qb.DocType("Press Role")
	rows = (
		frappe.qb.from_(PressRole)
		.where(PressRole.team == team)
		.select(
			PressRole.name,
			PressRole.title,
			*[getattr(PressRole, field) for field in PERMISSION_FIELDS],
		)
		.run(as_dict=True)
	)

	roles = []
	for role in rows:
		role_data: dict = {
			"label": role.title,
			"value": role.title,
			"name": role.name,
		}
		for field in PERMISSION_FIELDS:
			role_data[field] = role.get(field, False)
		roles.append(role_data)

	return cast("list[RoleDict]", roles)
