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

	def test_app_server_cpu_spike_flags_noisy_neighbor(self):
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
				"app_server_metrics": {
					"available": True,
					"cpu": {"available": True, "peak": 85.0, "mean": 30.0, "spike_detected": True},
				},
				"db_server_metrics": {},
				"server_advanced_analytics": {},
				"site_performance": {},
			}
		)

		self.assertIn("CPU spiked", report["likely_cause"])
		self.assertTrue(any("noisy neighbor" in step for step in report["recommended_next_steps"]))

	def test_db_server_cpu_spike_flags_isolation_issue(self):
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
				"app_server_metrics": {},
				"db_server_metrics": {
					"available": True,
					"cpu": {"available": True, "peak": 92.0, "mean": 40.0, "spike_detected": True},
				},
				"server_advanced_analytics": {},
				"site_performance": {},
			}
		)

		self.assertIn("Database server CPU spiked", report["likely_cause"])
		self.assertTrue(any("dedicated server" in step for step in report["recommended_next_steps"]))

	def test_slow_endpoint_flags_web_worker_cause(self):
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
				"app_server_metrics": {},
				"db_server_metrics": {},
				"server_advanced_analytics": {},
				"site_performance": {
					"available": True,
					"top_slow_endpoints": [
						{
							"path": "/api/method/frappe.desk.query_report.run",
							"avg_duration_s": 12.5,
							"peak_duration_s": 45.0,
						}
					],
				},
			}
		)

		self.assertIn("web workers", report["likely_cause"])
		self.assertTrue(any("Recorder" in step for step in report["recommended_next_steps"]))

	def test_fast_endpoints_do_not_trigger_evidence(self):
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
				"site_performance": {
					"available": True,
					"top_slow_endpoints": [
						{
							"path": "/api/method/frappe.client.get",
							"avg_duration_s": 0.3,
							"peak_duration_s": 0.8,
						}
					],
				},
			}
		)

		self.assertEqual(report["confidence"], "Low")
