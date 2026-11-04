import frappe
from frappe.tests.utils import FrappeTestCase

# The DPA (Schedule II, rows 2 and 13) promises a version log on every critical document.
CRITICAL_DOCTYPES = (
	"Account Request",
	"Audit Log",
	"Incident",
	"Incident Settings",
	"Invoice",
	"Mpesa Payment Record",
	"Payment Dispute",
	"Razorpay Mandate",
	"Razorpay Payment Record",
	"Remote File",
	"Server Snapshot",
	"Site",
	"Site Backup",
	"Site Partner Lead",
	"Site User",
	"Stripe Payment Method",
	"Support Access",
	"Team",
	"Team Deletion Request",
	"Team Member Impersonation",
	"User 2FA",
	"User SSH Key",
)


class TestTrackChanges(FrappeTestCase):
	def test_every_dpa_critical_doctype_has_track_changes_enabled(self):
		untracked = [doctype for doctype in CRITICAL_DOCTYPES if not frappe.get_meta(doctype).track_changes]
		self.assertEqual(untracked, [])
