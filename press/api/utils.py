import frappe
from press.press.doctype.brand_settings.brand_settings import (
	get_brand_details as _get_brand_details,
	get_brand_name as _get_brand_name,
)


@frappe.whitelist(allow_guest=True)
def get_brand_details():
	data = _get_brand_details()

	print(data)
	return _get_brand_details()


@frappe.whitelist(allow_guest=True)
def get_brand_name():
	return _get_brand_name() or "Frappe Cloud"
