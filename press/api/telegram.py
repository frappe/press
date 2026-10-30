# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import hmac

import frappe
from frappe.utils.password import get_decrypted_password

from press.telegram_utils import Telegram
from press.utils import log_error


@frappe.whitelist(allow_guest=True, xss_safe=True)
def hook(*args, **kwargs):
	verify_secret_token()
	try:
		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		client = Telegram()
		client.respond(kwargs.get("message", kwargs.get("edited_message")))

	except Exception:
		log_error("Telegram Webhook Error", args=args, kwargs=kwargs)
	finally:
		frappe.set_user("Guest")


def verify_secret_token():
	"""Reject requests that do not carry the secret token registered with setWebhook."""
	expected = get_decrypted_password(
		"Press Settings", "Press Settings", "telegram_webhook_secret", raise_exception=False
	)
	received = frappe.get_request_header("X-Telegram-Bot-Api-Secret-Token") or ""
	if not expected or not hmac.compare_digest(expected, received):
		frappe.throw("Invalid Telegram secret token", frappe.AuthenticationError)
