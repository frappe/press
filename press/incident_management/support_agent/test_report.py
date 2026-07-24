from frappe.tests.utils import FrappeTestCase

from press.incident_management.support_agent.report import generate_report


class TestSupportAgentReport(FrappeTestCase):
	def test_fatal_site_update_is_high_confidence(self):
		report = generate_report(
			{
				"site": {"name": "test.frappe.cloud", "status": "Active", "usage_percent": {}},
				"bench": {"status": "Active"},
				"deployments": [{"name": "update-1", "status": "Fatal", "creation": "now"}],
				"background_jobs": {},
				"backups": {},
				"domains": {},
				"incidents": [],
				"errors": {},
			}
		)

		self.assertIn("permanently", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_failure_state_site_update_is_medium_confidence(self):
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

		self.assertIn("recovery", report["likely_cause"])
		self.assertEqual(report["confidence"], "Medium")

	def test_recovered_site_update_produces_no_cause(self):
		report = generate_report(
			{
				"site": {"name": "test.frappe.cloud", "status": "Active", "usage_percent": {}},
				"bench": {"status": "Active"},
				"deployments": [{"name": "update-1", "status": "Recovered", "creation": "now"}],
				"background_jobs": {},
				"backups": {},
				"domains": {},
				"incidents": [],
				"errors": {},
			}
		)

		self.assertEqual(report["confidence"], "Low")

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

	def test_busy_db_cpu_with_heavy_query_points_at_slow_queries_not_volume(self):
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
				"db_server_metrics": {
					"available": True,
					"cpu": {"available": True, "peak": 92.0, "mean": 40.0, "spike_detected": True},
				},
				"slow_queries": {
					"available": True,
					"window_hours": 24,
					"log_count": 30,
					"top_queries": [
						{
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
							"count": 6,
							"total_duration_s": 24.0,
							"avg_duration_s": 4.0,
							"rows_examined": 900,
							"rows_sent": 90,
						}
					],
				},
			}
		)

		self.assertTrue(
			any("too-slow queries rather than query volume" in e for e in report["evidence"]),
			report["evidence"],
		)

	def test_busy_db_cpu_with_many_fast_queries_points_at_volume(self):
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
				"db_server_metrics": {
					"available": True,
					"cpu": {"available": True, "peak": 92.0, "mean": 40.0, "spike_detected": True},
				},
				"slow_queries": {
					"available": True,
					"window_hours": 24,
					"log_count": 400,
					"top_queries": [
						{
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
							"count": 380,
							"total_duration_s": 190.0,
							"avg_duration_s": 0.5,
							"rows_examined": 900,
							"rows_sent": 90,
						}
					],
				},
			}
		)

		self.assertTrue(
			any("query volume rather than a few too-slow queries" in e for e in report["evidence"]),
			report["evidence"],
		)

	def test_live_processlist_surfaces_longest_running_connection(self):
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
				"database_processes": {
					"available": True,
					"count": 42,
					"target_site_connections": 40,
					"busiest_site_connections": 40,
					"busiest_site_is_target": True,
					"processes": [
						{
							"site": "test.frappe.cloud",
							"is_target_site": True,
							"command": "Query",
							"seconds": 310,
							"state": "Sending data",
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
						}
					],
				},
			}
		)

		self.assertTrue(any("310s in state 'Sending data'" in e for e in report["evidence"]))
		self.assertTrue(any("processlist" in step for step in report["recommended_next_steps"]))

	def test_processlist_dominated_by_another_site_confirms_noisy_neighbor(self):
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
				"database_processes": {
					"available": True,
					"count": 50,
					"target_site_connections": 2,
					"busiest_site_connections": 44,
					"busiest_site_is_target": False,
					"processes": [
						{
							"site": "noisy.frappe.cloud",
							"is_target_site": False,
							"command": "Query",
							"seconds": 500,
							"state": "Sending data",
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
						}
					],
				},
			}
		)

		self.assertIn("Another tenant", report["likely_cause"])
		self.assertTrue(any("noisy neighbor confirmed" in e for e in report["evidence"]))
		self.assertTrue(any("dedicated database server" in step for step in report["recommended_next_steps"]))

	def test_processlist_dominated_by_the_site_itself_rules_out_noisy_neighbor(self):
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
				"database_processes": {
					"available": True,
					"count": 50,
					"target_site_connections": 46,
					"busiest_site_connections": 46,
					"busiest_site_is_target": True,
					"processes": [
						{
							"site": "test.frappe.cloud",
							"is_target_site": True,
							"command": "Query",
							"seconds": 500,
							"state": "Sending data",
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
						}
					],
				},
			}
		)

		self.assertNotIn("Another tenant", report["likely_cause"])
		self.assertTrue(any("the load is its own" in e for e in report["evidence"]))

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

	def test_database_error_in_web_log_flags_connectivity(self):
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
				"web_error_log": {
					"available": True,
					"error_count": 3,
					"recent_errors": [
						{
							"time": "2026-06-08 10:00:00 +0000",
							"level": "error",
							"description": "Error handling request /api/method/frappe.client.get",
							"exception": "OperationalError: (2003, \"Can't connect to MySQL server on '[REDACTED_IP]'\")",
						}
					],
				},
			}
		)

		self.assertIn("database connectivity", report["likely_cause"])
		self.assertTrue(any("database server" in step for step in report["recommended_next_steps"]))

	def test_import_error_in_web_log_flags_broken_state(self):
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
				"web_error_log": {
					"available": True,
					"error_count": 5,
					"recent_errors": [
						{
							"time": "2026-06-08 10:00:00 +0000",
							"level": "error",
							"description": "Error handling request /api/method/some.endpoint",
							"exception": "ImportError: No module named 'custom_app.hooks'",
						}
					],
				},
			}
		)

		self.assertIn("import errors", report["likely_cause"])
		self.assertTrue(any("deployment" in step for step in report["recommended_next_steps"]))

	def test_empty_web_error_log_produces_no_cause(self):
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
				"web_error_log": {"available": True, "error_count": 0, "recent_errors": []},
			}
		)

		self.assertEqual(report["confidence"], "Low")

	def test_500_worker_timeout_in_web_log_flags_critical(self):
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
				"web_error_log": {
					"available": True,
					"error_count": 2,
					"recent_errors": [
						{
							"time": "2026-06-08 10:00:00 +0000",
							"level": "critical",
							"description": "WORKER TIMEOUT (pid:1234)",
						}
					],
				},
			}
		)

		self.assertIn("CRITICAL", report["likely_cause"])
		self.assertTrue(any("web_error_log" in step for step in report["recommended_next_steps"]))

	def test_504_custom_app_endpoint_flagged_as_application_level(self):
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
					"has_custom_apps": True,
					"top_slow_endpoints": [
						{
							"path": "/api/method/custom_crm.api.get_leads",
							"avg_duration_s": 8.5,
							"peak_duration_s": 25.0,
							"spike_detected": False,
							"is_custom": True,
						}
					],
				},
			}
		)

		self.assertIn("Custom app", report["likely_cause"])
		self.assertTrue(any("Recorder" in step for step in report["recommended_next_steps"]))
		self.assertTrue(any("non-Frappe" in e for e in report["evidence"]))

	def test_504_spiky_endpoint_flagged_even_with_low_average(self):
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
					"has_custom_apps": False,
					"top_slow_endpoints": [
						{
							"path": "/api/method/frappe.desk.query_report.run",
							"avg_duration_s": 0.4,
							"peak_duration_s": 18.0,
							"spike_detected": True,
							"is_custom": False,
						}
					],
				},
			}
		)

		self.assertTrue(any("spike" in e.lower() for e in report["evidence"]))
		self.assertTrue(any("Recorder" in step for step in report["recommended_next_steps"]))

	def test_504_frappe_endpoint_slow_flags_web_workers(self):
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
					"has_custom_apps": False,
					"top_slow_endpoints": [
						{
							"path": "/api/method/frappe.desk.reportview.get",
							"avg_duration_s": 5.0,
							"peak_duration_s": 9.0,
							"spike_detected": False,
							"is_custom": False,
						}
					],
				},
			}
		)

		self.assertIn("web workers", report["likely_cause"])
		self.assertTrue(any("Recorder" in step for step in report["recommended_next_steps"]))

	def test_502_stopped_gunicorn_web_process_flags_direct_cause(self):
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
				"bench_processes": {
					"available": True,
					"total": 6,
					"stopped_count": 1,
					"stopped_processes": [
						{
							"name": "frappe-bench-frappe-web",
							"status": "Fatal",
							"message": "Exited too quickly (process log may have details)",
						}
					],
				},
			}
		)

		self.assertIn("Gunicorn", report["likely_cause"])
		self.assertIn("502", report["likely_cause"])
		self.assertTrue(any("web.error.log" in step for step in report["recommended_next_steps"]))

	def test_502_all_processes_running_produces_no_process_cause(self):
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
				"bench_processes": {
					"available": True,
					"total": 6,
					"stopped_count": 0,
					"stopped_processes": [],
				},
			}
		)

		self.assertFalse(any("Gunicorn" in c for c in [report["likely_cause"]]))

	def test_failed_agent_jobs_are_evidence_but_never_the_likely_cause(self):
		report = generate_report(
			{
				"site": {"name": "test.frappe.cloud", "status": "Active", "usage_percent": {}},
				"bench": {"status": "Active"},
				"deployments": [],
				"background_jobs": {},
				"backups": {},
				"domains": {},
				"incidents": [],
				"errors": {"window_hours": 24, "failed_job_count": 7},
			}
		)

		self.assertTrue(any("7 agent jobs failed" in e for e in report["evidence"]))
		self.assertIn("No obvious platform-side issue", report["likely_cause"])
		self.assertEqual(report["confidence"], "Low")

	def test_slow_query_scanning_too_many_rows_flags_missing_index(self):
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
				"slow_queries": {
					"available": True,
					"window_hours": 24,
					"log_count": 40,
					"top_queries": [
						{
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
							"count": 20,
							"total_duration_s": 60.0,
							"avg_duration_s": 3.0,
							"rows_examined": 500000,
							"rows_sent": 12,
						}
					],
				},
			}
		)

		self.assertIn("index is missing", report["likely_cause"])
		self.assertTrue(any("tabToDo" in e for e in report["evidence"]))

	def test_slow_query_below_duration_threshold_produces_no_cause(self):
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
				"slow_queries": {
					"available": True,
					"window_hours": 24,
					"log_count": 2,
					"top_queries": [
						{
							"query": "SELECT `name` FROM `tabToDo` WHERE `owner` = ?",
							"count": 2,
							"total_duration_s": 2.4,
							"avg_duration_s": 1.2,
							"rows_examined": 100,
							"rows_sent": 40,
						}
					],
				},
			}
		)

		self.assertEqual(report["confidence"], "Low")
		self.assertTrue(any("Slowest database query" in e for e in report["evidence"]))

	def test_slow_query_share_dominated_by_another_site_confirms_noisy_neighbor(self):
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
				"database_slow_query_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 4.0,
					"busiest_site": "noisy.frappe.cloud",
					"busiest_site_share_percent": 81.0,
					"busiest_site_is_target": False,
				},
			}
		)

		self.assertIn("Another tenant", report["likely_cause"])
		self.assertTrue(any("81.0% of slow-query time" in e for e in report["evidence"]))

	def test_slow_query_share_dominated_by_the_site_itself_rules_out_noisy_neighbor(self):
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
				"database_slow_query_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 88.0,
					"busiest_site": "test.frappe.cloud",
					"busiest_site_share_percent": 88.0,
					"busiest_site_is_target": True,
				},
			}
		)

		self.assertNotIn("Another tenant", report["likely_cause"])
		self.assertTrue(any("the load is its own" in e for e in report["evidence"]))

	def test_request_share_dominated_by_a_site_on_the_same_bench_flags_shared_workers(self):
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
				"app_server_request_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 5.0,
					"busiest_site": "noisy.frappe.cloud",
					"busiest_site_share_percent": 76.0,
					"busiest_site_is_target": False,
					"busiest_site_shares_bench": True,
				},
			}
		)

		self.assertIn("same bench", report["likely_cause"])
		self.assertTrue(any("share gunicorn workers" in s for s in report["recommended_next_steps"]))

	def test_request_share_dominated_by_a_site_on_another_bench_flags_noisy_neighbor(self):
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
					"cpu": {"available": True, "peak": 97.0, "mean": 40.0, "spike_detected": True},
				},
				"app_server_request_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 5.0,
					"busiest_site": "noisy.frappe.cloud",
					"busiest_site_share_percent": 76.0,
					"busiest_site_is_target": False,
					"busiest_site_shares_bench": False,
				},
			}
		)

		self.assertTrue(any("noisy neighbor confirmed" in e for e in report["evidence"]))
		self.assertTrue(any("move the heavy tenant" in step for step in report["recommended_next_steps"]))

	def test_request_share_dominated_by_the_site_itself_rules_out_noisy_neighbor(self):
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
				"app_server_request_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 91.0,
					"busiest_site": "test.frappe.cloud",
					"busiest_site_share_percent": 91.0,
					"busiest_site_is_target": True,
				},
			}
		)

		self.assertNotIn("Another", report["likely_cause"])
		self.assertTrue(any("request time on the app server" in e for e in report["evidence"]))

	def test_busier_neighbor_on_another_bench_is_not_noisy_when_the_server_had_headroom(self):
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
					"cpu": {"available": True, "peak": 74.0, "mean": 30.0, "spike_detected": True},
				},
				"app_server_request_share": {
					"available": True,
					"window_hours": 24,
					"target_site_share_percent": 5.0,
					"busiest_site": "noisy.frappe.cloud",
					"busiest_site_share_percent": 76.0,
					"busiest_site_is_target": False,
					"busiest_site_shares_bench": False,
				},
			}
		)

		self.assertTrue(any("it had headroom" in e for e in report["evidence"]))
		self.assertFalse(any("move the heavy tenant" in step for step in report["recommended_next_steps"]))
