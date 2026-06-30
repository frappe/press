from typing import TypedDict, cast

import frappe
import frappe.utils
from frappe.types.DF import Data
from pypika import Not
from pypika import functions as fn
from pypika.terms import ValueWrapper

# Permission fields that apply to both predefined and custom roles.
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

# Predefined roles and their default permission configuration.
# These are built-in roles available to every team.
PREDEFINED_ROLES: list[dict] = [
	{
		"label": "Admin",
		"value": "Admin",
		"name": None,
		"is_predefined": True,
		"admin_access": True,
		"allow_apps": True,
		"allow_bench_creation": True,
		"allow_billing": True,
		"allow_contribution": False,
		"allow_customer": False,
		"allow_dashboard": False,
		"allow_leads": False,
		"allow_partner": False,
		"allow_server_creation": True,
		"allow_site_creation": True,
		"allow_webhook_configuration": True,
		"all_release_groups": False,
		"all_servers": False,
		"all_sites": False,
	},
	{
		"label": "Developer",
		"value": "Developer",
		"name": None,
		"is_predefined": True,
		"admin_access": False,
		"allow_apps": True,
		"allow_bench_creation": True,
		"allow_billing": False,
		"allow_contribution": False,
		"allow_customer": False,
		"allow_dashboard": False,
		"allow_leads": False,
		"allow_partner": False,
		"allow_server_creation": True,
		"allow_site_creation": True,
		"allow_webhook_configuration": True,
		"all_release_groups": False,
		"all_servers": False,
		"all_sites": False,
	},
	{
		"label": "Member",
		"value": "Member",
		"name": None,
		"is_predefined": True,
		"admin_access": False,
		"allow_apps": False,
		"allow_bench_creation": False,
		"allow_billing": False,
		"allow_contribution": False,
		"allow_customer": False,
		"allow_dashboard": False,
		"allow_leads": False,
		"allow_partner": False,
		"allow_server_creation": False,
		"allow_site_creation": False,
		"allow_webhook_configuration": False,
		"all_release_groups": False,
		"all_servers": False,
		"all_sites": False,
	},
	{
		"label": "Viewer",
		"value": "Viewer",
		"name": None,
		"is_predefined": True,
		"admin_access": False,
		"allow_apps": False,
		"allow_bench_creation": False,
		"allow_billing": False,
		"allow_contribution": False,
		"allow_customer": False,
		"allow_dashboard": False,
		"allow_leads": False,
		"allow_partner": False,
		"allow_server_creation": False,
		"allow_site_creation": False,
		"allow_webhook_configuration": False,
		"all_release_groups": False,
		"all_servers": False,
		"all_sites": False,
	},
]


def get_members(team: str):
	"""
	Get a list of team members for a given team.
	"""
	Member = frappe.qb.DocType("Team Member")
	MemberResource = frappe.qb.DocType("Team Member Resource")
	User = frappe.qb.DocType("User")
	from pypika import functions as fn

	return (
		frappe.qb.from_(Member)
		.inner_join(User)
		.on(Member.user == User.name)
		.left_join(MemberResource)
		.on((MemberResource.user == Member.user) & (MemberResource.team == Member.parent))
		.where(Member.parent == team)
		.groupby(
			Member.name,
			Member.creation,
			Member.role,
			Member.all_servers,
			Member.all_release_groups,
			Member.all_sites,
			User.email,
			User.full_name,
			User.user_image,
		)
		.select(
			Member.name,
			Member.creation.as_("date"),
			Member.role,
			Member.all_servers,
			Member.all_release_groups,
			Member.all_sites,
			fn.Count(MemberResource.name).as_("resource_count"),
			ValueWrapper("Active").as_("status"),
			User.email,
			User.full_name,
			User.user_image,
		)
		.run(as_dict=True)
	)


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
		.select(
			AccountRequest.name,
			AccountRequest.email,
			AccountRequest.request_key_expiration_time.as_("date"),
			fn.Coalesce(PressRole.title, AccountRequest.press_role).as_("press_role"),
			PressRole.name.as_("press_role_name"),
			ValueWrapper("Pending").as_("status"),
			User.full_name,
			User.user_image,
		)
		.run(as_dict=True)
	)


class RoleDict(TypedDict):
	label: str
	value: str
	name: str | None
	is_predefined: bool
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
	Get a list of roles that can be assigned to team members. This includes
	both predefined roles (Admin, Developer, Member, Viewer) and any custom
	roles defined in the Press Role doctype for the given team.

	Each role includes its full permission configuration so the frontend can
	display granular permissions for each role.
	"""
	roles = [dict(role) for role in PREDEFINED_ROLES]

	if team:
		PressRole = frappe.qb.DocType("Press Role")
		custom_roles = (
			frappe.qb.from_(PressRole)
			.where(PressRole.team == team)
			.select(
				PressRole.name,
				PressRole.title,
				*[getattr(PressRole, field) for field in PERMISSION_FIELDS],
			)
			.run(as_dict=True)
		)
		for role in custom_roles:
			role_data = {
				"label": role.title,
				"value": role.title,
				"name": role.name,
				"is_predefined": False,
			}
			for field in PERMISSION_FIELDS:
				role_data[field] = role.get(field, False)
			roles.append(role_data)

	return cast("list[RoleDict]", roles)


def remove_member(team: str, member: str):
	"""
	Remove a member from the team. This will delete the Team Member record for
	the user.
	"""
	d = frappe.get_doc("Team", team)
	for m in d.team_members.copy():
		if m.name == member:
			d.team_members.remove(m)
	d.save()
