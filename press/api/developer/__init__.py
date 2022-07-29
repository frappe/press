import frappe


class InvalidSecretKeyError(Exception):
	http_status_code = 401


def raise_invalid_key_error():
	frappe.throw("Please provide a valid secret key.", InvalidSecretKeyError)
