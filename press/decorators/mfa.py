import functools

import frappe

from press.api import account


def enabled(raise_error: bool = False):
	def get_user():
		return frappe.session.user

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			user = get_user()
			if user and account.is_2fa_enabled(user):
				return fn(*args, **kwargs)
			if raise_error:
				msg = "Two-factor authentication is not enabled."
				raise frappe.PermissionError(msg)
			return None

		return inner

	return wrapper


def verify(code_key: str = "totp_code", raise_error: bool = False):
	def get_user():
		return frappe.session.user

	def get_code():
		return frappe.request.form.get(code_key)

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			user = get_user()
			code = get_code()
			if user and not account.is_2fa_enabled(user):
				return fn(*args, **kwargs)
			if user and code and account.verify_2fa(user, code):
				return fn(*args, **kwargs)
			if raise_error:
				msg = "Two-factor authentication verification failed."
				raise frappe.PermissionError(msg)
			return None

		return inner

	return wrapper
