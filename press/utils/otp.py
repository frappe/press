from __future__ import annotations

import os

import frappe

# What a code was issued for. A code handed out to verify a signup must not work
# to log in, so each purpose gets its own key.
SIGNUP = "signup"
LOGIN = "login"
TWO_FACTOR_RECOVERY = "2fa-recovery"

# How long a code stays good for. A signup code is mailed alongside the
# setup-account link, so it lasts as long as that link does — see
# `request_key_expiration_time`. Codes that open an account that already exists
# get minutes, not a day.
EXPIRES_IN = {
	SIGNUP: 24 * 60 * 60,
	LOGIN: 10 * 60,
	TWO_FACTOR_RECOVERY: 10 * 60,
}


def generate_otp():
	"""Generates a cryptographically secure random OTP"""

	return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


class OneTimePassword:
	"""A one-time password held in the cache, hashed, until it expires.

	These used to live on Account Request, which tied logging in to still having
	the record written when you signed up. Accounts whose request was never
	created, or had since been cleaned up, could not log in at all.

	The identifier is whatever the code is about: an email for logging in, an
	Account Request for verifying a signup.
	"""

	def __init__(self, purpose: str, identifier: str):
		self.purpose = purpose
		self.identifier = identifier
		self.expires_in = EXPIRES_IN[purpose]

	@property
	def key(self) -> str:
		return f"press_otp:{self.purpose}:{self.identifier}"

	def generate(self) -> str:
		code = str(generate_otp())
		if frappe.conf.developer_mode and frappe.local.dev_server:
			code = "111111"

		frappe.cache.set_value(
			self.key,
			{"hash": frappe.utils.sha256_hash(code), "generated_at": frappe.utils.now_datetime()},
			expires_in_sec=self.expires_in,
		)

		return code

	def verify(self, code: str | int) -> bool:
		issued = frappe.cache.get_value(self.key)
		if not issued:
			return False

		return issued["hash"] == frappe.utils.sha256_hash(str(code))

	def consume(self, code: str | int) -> bool:
		"""Check the code and spend it, so that only one caller can use it.

		Requests arriving together can all read the same code before any of them
		removes it, so reading cannot decide who wins. Removing can: Redis says
		how many keys it actually deleted, and only the caller that deleted this
		one gets to go on.
		"""
		if not self.verify(code):
			return False

		return self.clear()

	def clear(self) -> bool:
		"""Whether this call was the one that removed the code."""
		key = frappe.cache.make_key(self.key)
		frappe.local.cache.pop(key, None)

		return bool(frappe.cache.delete(key))

	@property
	def seconds_since_generated(self) -> int | None:
		"""None when nothing was issued, or what was issued has expired."""
		issued = frappe.cache.get_value(self.key)
		if not issued:
			return None

		return (frappe.utils.now_datetime() - issued["generated_at"]).seconds
