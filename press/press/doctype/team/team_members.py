import frappe
import frappe.utils
from pypika import Not
from pypika.terms import ValueWrapper


def get_members(team: str):
	"""
	Get a list of team members for a given team.
	"""
	Member = frappe.qb.DocType("Team Member")
	User = frappe.qb.DocType("User")
	return (
		frappe.qb.from_(Member)
		.inner_join(User)
		.on(Member.user == User.name)
		.where(Member.parent == team)
		.select(
			Member.name,
			Member.creation.as_("date"),
			ValueWrapper("Active").as_("status"),
			ValueWrapper("Developer").as_("role"),
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


def get_roles(team: str):
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
