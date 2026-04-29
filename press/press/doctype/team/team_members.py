import frappe
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
			Member.creation.as_("joined"),
			ValueWrapper("Active").as_("status"),
			ValueWrapper("Developer").as_("role"),
			User.email,
			User.full_name,
			User.user_image,
		)
		.run(as_dict=True)
	)
