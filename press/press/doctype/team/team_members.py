from typing import TypedDict

import frappe
import frappe.utils
from frappe.types.DF import Data
from pypika import Not
from pypika.terms import ValueWrapper


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
	User = frappe.qb.DocType("User")
	return (
		frappe.qb.from_(AccountRequest)
		.left_join(User)
		.on(AccountRequest.email == User.email)
		.where(AccountRequest.team == team)
		.where(Not(AccountRequest.invited_by.isnull()))
		.where(AccountRequest.request_key_expiration_time > frappe.utils.now_datetime())
		.select(
			AccountRequest.name,
			AccountRequest.email,
			AccountRequest.request_key_expiration_time.as_("date"),
			ValueWrapper("Pending").as_("status"),
			User.full_name,
			User.user_image,
		)
		.run(as_dict=True)
	)


class RoleDict(TypedDict):
	label: str
	value: str


def get_roles(team: Data | None) -> list[RoleDict]:
	"""
	Get a list of roles that can be assigned to team members. This should
	include both predefined roles and any custom roles.
	"""
	_ = team  # Team is not used currently, but we can use it in the future to fetch roles specific to a team.
	return [
		{"label": "Admin", "value": "Admin"},
		{"label": "Member", "value": "Member"},
		{"label": "Developer", "value": "Developer"},
		{"label": "Viewer", "value": "Viewer"},
	]


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
