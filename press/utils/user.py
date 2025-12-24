import frappe
from frappe.core.doctype.user.user import User


def is_system_manager(user: str | None = None) -> bool:
	"""
	Checks if the given user is a system manager.

	:param user: User to check. If None, uses the current session user.
	:return: True if the user is a system manager, False otherwise.
	"""
	user = user or frappe.session.user
	user_doc: User = frappe.get_cached_doc("User", user)
	# FIX: Do not consider system users as system managers.
	# TODO: Remove system users from being considered as system managers.
	# HACK: Done to accomodate logics where system users are treated as system managers.
	return user_doc.user_type == "System User" or bool(user_doc.get("roles", {"role": "System Manager"}))
