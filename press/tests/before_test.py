# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import os

import frappe
from frappe.model.document import Document


def doc_equal(self: Document, other: Document) -> bool:
	"""Partial equality checking of Document object"""
	if not isinstance(other, Document):
		return False
	if self.doctype == other.doctype and self.name == other.name:
		return True
	return False


def execute():
	settings = frappe.get_single("Press Settings")
	if not (settings.stripe_secret_key and settings.stripe_publishable_key):
		create_test_stripe_credentials()
	import cssutils

	# Silence the cssutils errors that are mostly pointless
	cssutils.log.setLevel(50)

	# Monkey patch certain methods for when tests are running
	Document.__eq__ = doc_equal


def create_test_stripe_credentials():
	publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY")
	secret_key = os.environ.get("STRIPE_SECRET_KEY")

	if publishable_key and secret_key:
		frappe.db.set_single_value(
			"Press Settings", "stripe_publishable_key", publishable_key
		)
		frappe.db.set_single_value("Press Settings", "stripe_secret_key", secret_key)
