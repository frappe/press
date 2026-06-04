from frappe.tests.utils import FrappeTestCase

from press.incident_management.support_agent.report import generate_report


class TestSupportAgentReport(FrappeTestCase):
	def test_flags_failed_site_update(self):
		report = generate_report(
			{
				"site": {"name": "test.frappe.cloud", "status": "Active", "usage_percent": {}},
				"bench": {"status": "Active"},
				"deployments": [{"name": "update-1", "status": "Failure", "creation": "now"}],
				"background_jobs": {},
				"backups": {},
				"domains": {},
				"incidents": [],
				"errors": {},
			}
		)

		self.assertEqual(report["likely_cause"], "Recent site update failed or was cancelled.")
		self.assertEqual(report["confidence"], "High")

	def test_returns_low_confidence_when_no_signals(self):
		report = generate_report(
			{
				"site": {"name": "test.frappe.cloud", "status": "Active", "usage_percent": {}},
				"bench": {"status": "Active"},
				"deployments": [],
				"background_jobs": {},
				"backups": {},
				"domains": {},
				"incidents": [],
				"errors": {},
			}
		)

		self.assertEqual(report["confidence"], "Low")
