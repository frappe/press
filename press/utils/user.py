from contextlib import contextmanager

import frappe

if frappe.TYPE_CHECKING:
	from frappe.core.doctype.user.user import User


def is_dashboard_request() -> bool:
	"""Whether the request comes from the dashboard, which sends the team in X-Press-Team."""
	headers = getattr(getattr(frappe.local, "request", None), "headers", None)
	return bool(headers and headers.get("X-Press-Team"))


def is_staff_on_dashboard(user: str | None = None) -> bool:
	"""On the dashboard, every employee gets the access of a customer, whatever their roles."""
	user = user or frappe.session.user
	return is_dashboard_request() and user != "Administrator" and is_desk_user(user)


def is_employee() -> bool:
	"""Every employee is a desk user or holds Press Employee, the role for dashboard-only staff."""
	return is_desk_user() or "Press Employee" in frappe.get_roles()


def is_system_manager(user: str | None = None) -> bool:
	"""
	Checks if the given user is a system manager.

	:param user: User to check. If None, uses the current session user.
	:return: True if the user is a system manager, False otherwise.
	"""
	user = user or frappe.session.user
	if is_staff_on_dashboard(user):
		return False
	user_doc: User = frappe.get_cached_doc("User", user)
	# FIX: Do not consider system users as system managers.
	# TODO: Remove system users from being considered as system managers.
	# HACK: Done to accommodate logics where system users are treated as system managers.
	return user_doc.user_type == "System User" or bool(user_doc.get("roles", {"role": "System Manager"}))


def is_desk_user(user: str | None = None) -> bool:
	"""
	Checks if the given user is a system user.

	:param user: User to check. If None, uses the current session user.
	:return: True if the user is a system user, False otherwise.
	"""
	user = user or frappe.session.user
	user_doc: User = frappe.get_cached_doc("User", user)
	return user_doc.user_type == "System User"


@contextmanager
def as_administrator():
	"""Run the block as Administrator, and keep the caller's session intact.

	`frappe.set_user` overwrites the sid and data of the live session. Frappe then
	saves the broken session at the end of the request, which logs the user out.
	"""
	session = frappe.session.copy()
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(session["user"])
		frappe.session.update(session)
