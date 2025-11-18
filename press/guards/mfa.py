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


def verify(user_key: str = "user", code_key: str = "totp_code", raise_error: bool = False):
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
