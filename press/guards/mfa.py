import functools

import frappe
import pyotp
from frappe import auth


def enabled(user_key: str = "user", raise_error: bool = False):
	"""
	Guard to check if two-factor authentication is enabled for a user.

	:param user_key: The key to retrieve the user from the request form if the session user is "Guest". Defaults to "user".
	:param raise_error: Whether to raise a PermissionError if 2FA is not enabled. Defaults to False.
	:raises frappe.PermissionError: If 2FA is not enabled and `raise_error` is True.
	"""

	def get_user() -> str:
		if frappe.session.user == "Guest":
			return (frappe.request.json or frappe.request.form).get(user_key, frappe.session.user)
		return frappe.session.user

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			if frappe.get_value("User 2FA", get_user(), "enabled"):
				return fn(*args, **kwargs)
			if raise_error:
				message = "Two-factor authentication is not enabled."
				frappe.throw(message, frappe.PermissionError)
			return None

		return inner

	return wrapper


def verify(user_key: str = "user", code_key: str = "totp_code", raise_error: bool = False):  # noqa: C901
	"""
	Guard to verify two-factor authentication for a user.

	:param user_key: The key to retrieve the user from the request form if the session user is "Guest". Defaults to "user".
	:param code_key: The key to retrieve the TOTP code from the request form. Defaults to "totp_code".
	:param raise_error: Whether to raise a PermissionError if 2FA verification fails. Defaults to False.
	:raises frappe.PermissionError: If 2FA verification fails and `raise_error` is True.
	"""

	def get_user() -> str:
		if frappe.session.user == "Guest":
			return (frappe.request.json or frappe.request.form).get(user_key, frappe.session.user)
		return frappe.session.user

	def get_code() -> str:
		return (frappe.request.json or frappe.request.form).get(code_key, "")

	def verify_code(user: str, code: str):
		secret = auth.get_decrypted_password("User 2FA", user, "totp_secret")
		return secret and pyotp.TOTP(secret).verify(code)

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			user = get_user()
			code = get_code()

			if user and not frappe.get_value("User 2FA", user, "enabled"):
				return fn(*args, **kwargs)
			if user and code and verify_code(user, code):
				return fn(*args, **kwargs)
			if raise_error:
				message = "Two-factor authentication verification failed."
				frappe.throw(message, frappe.PermissionError)
			return None

		return inner

	return wrapper


def ensure_for_team(team: str | None) -> None:
	"""Stop a member without 2FA from using a team that enforces it."""
	if not team or is_exempt_from_team_2fa():
		return
	if not frappe.db.get_value("Team", team, "enforce_2fa"):
		return
	if frappe.db.get_value("User 2FA", frappe.session.user, "enabled"):
		return
	frappe.throw(
		f"Team {team} requires two-factor authentication. Enable it to continue.",
		frappe.PermissionError,
	)


def is_exempt_from_team_2fa() -> bool:
	return frappe.session.data.user_type == "System User" or is_sessionless() or is_team_doc_read()


def is_sessionless() -> bool:
	# API key and OAuth logins call frappe.set_user, which sets the sid to the user
	return frappe.session.sid == frappe.session.user


def is_team_doc_read() -> bool:
	# The dashboard loads the Team doc to show the "Enable 2FA" page
	form = frappe.form_dict
	return form.cmd == "press.api.client.get" and form.doctype == "Team"
