import frappe

from unittest import TestCase
from press.api.billing import validate_gst


VALID_GSTINS = [
	{"gstin": "27AALFV4847R1Z2", "state": "Maharashtra", "country": "India"},
	{"gstin": "24APJPM3743A1Z9", "state": "Gujarat", "country": "India"},
	{"gstin": "33AASCA0911D1Z5", "state": "Tamil Nadu", "country": "India"},
	{"gstin": "09AAACU2759F1Z8", "state": "Uttar Pradesh", "country": "India"},
	{"gstin": "27BEDPK4339A1ZV", "state": "Maharashtra", "country": "India"},
	{"gstin": "33AAHCG3162B1Z5", "state": "Tamil Nadu", "country": "India"},
	{"gstin": "24BAVPS0504H1ZM", "state": "Gujarat", "country": "India"},
	{"gstin": "20AAECF5232E1ZB", "state": "Jharkhand", "country": "India"},
	{"gstin": "32AAICR8672C1ZC", "state": "Kerala", "country": "India"},
	{"gstin": "29AARFP2719A1Z6", "state": "Karnataka", "country": "India"},
]


INVALID_GSTINS = [
	{"gstin": "33AALCM8589JIZP", "state": "Tamil Nadu", "country": "India"},
	{"gstin": "33ABQFA7655JIZZ", "state": "Tamil Nadu", "country": "India"},
	{"gstin": "08AFHPK4336H12E", "state": "Rajasthan", "country": "India"},
]


class TestBillingUtils(TestCase):
	def test_validate_gstin_with_invalid(self):
		for obj in INVALID_GSTINS:
			self.assertRaises(frappe.ValidationError, validate_gst, obj)

	def test_validate_gstin_with_valid(self):
		for obj in VALID_GSTINS:
			self.assertIsNone(
				validate_gst(obj), f"{obj} has a valid GSTIN, but the validate function throws!"
			)
