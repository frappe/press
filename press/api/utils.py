import frappe
from press.press.doctype.brand_settings.brand_settings import (
	get_brand_details as _get_brand_details,
	get_brand_name as _get_brand_name,
	get_onboarding_message,
)


@frappe.whitelist(allow_guest=True)
def get_brand_details():
	return _get_brand_details()


@frappe.whitelist(allow_guest=True)
def get_brand_name():
	return _get_brand_name() or "Frappe Cloud"


@frappe.whitelist(allow_guest=True)
def get_onboarding_details():
	return {"message": get_onboarding_message()}
