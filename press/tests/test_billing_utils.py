from unittest import TestCase

import frappe

from press.api.billing import validate_gst

# NIF (Numero d'Identification Fiscale) test data for Algeria
VALID_NIFS = [
	{"gstin": "000016000000000", "country": "Algeria"},
	{"gstin": "000031000000000", "country": "Algeria"},
	{"gstin": "000042000000000", "country": "Algeria"},
]


INVALID_NIFS = [
	{"gstin": "12345", "country": "Algeria"},
	{"gstin": "ABCDEFGHIJKLMNO", "country": "Algeria"},
	{"gstin": "12345678901234X", "country": "Algeria"},
]


class TestBillingUtils(TestCase):
	def test_validate_nif_with_invalid(self):
		for obj in INVALID_NIFS:
			self.assertRaises(frappe.ValidationError, validate_gst, obj)

	def test_validate_nif_with_valid(self):
		for obj in VALID_NIFS:
			self.assertIsNone(
				validate_gst(obj), f"{obj} has a valid NIF, but the validate function throws!"
			)
