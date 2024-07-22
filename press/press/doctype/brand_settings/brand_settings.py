# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BrandSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand_logo: DF.AttachImage | None
		brand_name: DF.Data | None
		cookie_policy: DF.Data | None
		footer_logo: DF.AttachImage | None
		onboarding_message: DF.Text | None
		privacy_policy: DF.Data | None
		terms_of_service: DF.Data | None
	# end: auto-generated types

	pass


def get_brand_details():
	brand_details = frappe.get_cached_doc("Brand Settings")

	return {
		"brand_logo": brand_details.get("brand_logo"),
		"brand_name": brand_details.get("brand_name") or "Frappe Cloud",
		"footer_logo": brand_details.get("footer_logo"),
		"terms_of_service": brand_details.get("terms_of_service")
		or "https://frappecloud.com/terms",
		"cookie_policy": brand_details.get("cookie_policy")
		or "https://frappecloud.com/cookie-policy",
		"privacy_policy": brand_details.get("privacy_policy")
		or "https://frappecloud.com/privacy",
	}


def get_brand_name():
	brand_details = frappe.get_cached_doc("Brand Settings")
	return brand_details.get("brand_name") or "Frappe Cloud"


def get_onboarding_message():
	return frappe.db.get_single_value("Brand Settings", "onboarding_message")
