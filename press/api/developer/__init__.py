import frappe
from frappe import _


class InvalidSecretKeyError(Exception):
	http_status_code = 401


def raise_invalid_key_error():
	frappe.throw(_("Please provide a valid secret key."), InvalidSecretKeyError)
