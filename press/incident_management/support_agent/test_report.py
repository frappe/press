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

	def _base(self, **overrides):
		payload = {
			"site": {"name": "test.frappe.cloud", "status": "Active", "server": "s1", "usage_percent": {}},
			"bench": {"status": "Active"},
			"deployments": [],
			"background_jobs": {},
			"backups": {},
			"domains": {},
			"incidents": [],
			"errors": {},
		}
		payload.update(overrides)
		return payload

	def test_db_disk_full_is_high_confidence_500_cause(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"disk": {"available": True, "percent": 99.2, "full": True},
				}
			)
		)

		self.assertIn("Database server disk is full", report["likely_cause"])
		self.assertIn("500", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_app_disk_full_is_flagged_but_not_necessarily_500(self):
		report = generate_report(
			self._base(
				app_server_metrics={
					"available": True,
					"has_data": True,
					"disk": {"available": True, "percent": 98.5, "full": True},
				}
			)
		)

		self.assertIn("App server disk is full", report["likely_cause"])
		self.assertIn("not always 500", report["likely_cause"])

	def test_disk_below_threshold_is_not_full(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"disk": {"available": True, "percent": 91.0, "full": False},
				}
			)
		)

		self.assertEqual(report["confidence"], "Low")

	def test_both_servers_silent_with_healthy_monitor_flags_outage(self):
		report = generate_report(
			self._base(
				app_server_metrics={"available": True, "has_data": False},
				db_server_metrics={"available": True, "has_data": False},
				monitor_health={"available": True, "has_data": True},
			)
		)

		self.assertIn("both", report["likely_cause"].lower())
		self.assertEqual(report["confidence"], "High")

	def test_both_servers_silent_with_dead_monitor_blames_monitor(self):
		report = generate_report(
			self._base(
				app_server_metrics={"available": True, "has_data": False},
				db_server_metrics={"available": True, "has_data": False},
				monitor_health={"available": True, "has_data": False},
			)
		)

		self.assertTrue(any("monitoring server" in e for e in report["evidence"]))
		# Monitor being down is a caveat, not a customer-facing cause.
		self.assertEqual(report["confidence"], "Low")

	def test_single_server_silent_flags_that_server_down(self):
		report = generate_report(
			self._base(
				app_server_metrics={"available": True, "has_data": False},
				db_server_metrics={"available": True, "has_data": True, "cpu": {}},
				monitor_health={"available": True, "has_data": True},
			)
		)

		self.assertIn("App server appears to be down", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_db_iops_spike_without_iowait_is_not_a_cause(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"cpu": {"available": True, "spike_detected": False},
					"iops": {"available": True, "peak": 5000, "mean": 1000, "spike_detected": True},
					"iowait": {"available": True, "peak": 3.0, "spike_detected": False},
				}
			)
		)

		self.assertEqual(report["confidence"], "Low")
		self.assertTrue(any("unlikely to be the bottleneck" in e for e in report["evidence"]))

	def test_db_iops_spike_with_high_iowait_flags_io_bound(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"cpu": {"available": True, "spike_detected": False},
					"iops": {"available": True, "peak": 5000, "mean": 1000, "spike_detected": True},
					"iowait": {"available": True, "peak": 45.0, "mean": 10.0, "spike_detected": True},
				}
			)
		)

		self.assertIn("I/O-bound", report["likely_cause"])

	def test_cluster_only_incident_is_not_a_cause(self):
		report = generate_report(
			self._base(
				incidents=[{"name": "INC-1", "server": "other-server", "cluster": "c1", "creation": "now"}]
			)
		)

		self.assertTrue(any("unlikely to be the cause" in e for e in report["evidence"]))
		self.assertEqual(report["confidence"], "Low")

	def test_incident_on_own_server_is_a_cause(self):
		report = generate_report(
			self._base(incidents=[{"name": "INC-1", "server": "s1", "cluster": "c1", "creation": "now"}])
		)

		self.assertIn("own server", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_recent_custom_slow_endpoint_is_high_confidence(self):
		report = generate_report(
			self._base(
				site_performance={
					"available": True,
					"has_custom_apps": True,
					"recent_window_hours": 1,
					"top_slow_endpoints": [],
					"top_slow_endpoints_recent": [
						{
							"path": "/api/method/custom_crm.api.get_leads",
							"avg_duration_s": 6.0,
							"peak_duration_s": 12.0,
							"is_custom": True,
						}
					],
				}
			)
		)

		self.assertIn("last hour", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_multiple_signals_prompt_earliest_signal_correlation(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"cpu": {"available": True, "peak": 95.0, "mean": 40.0, "spike_detected": True},
				},
				site_performance={
					"available": True,
					"has_custom_apps": False,
					"top_slow_endpoints": [
						{
							"path": "/api/method/frappe.desk.reportview.get",
							"avg_duration_s": 6.0,
							"peak_duration_s": 9.0,
							"is_custom": False,
						}
					],
				},
			)
		)

		self.assertTrue(any("started earliest" in step for step in report["recommended_next_steps"]))

	def test_single_signal_has_no_correlation_note(self):
		report = generate_report(
			self._base(
				db_server_metrics={
					"available": True,
					"has_data": True,
					"cpu": {"available": True, "peak": 95.0, "mean": 40.0, "spike_detected": True},
				}
			)
		)

		self.assertFalse(any("started earliest" in step for step in report["recommended_next_steps"]))

	def test_probe_down_flags_site_unreachable(self):
		report = generate_report(
			self._base(site_uptime={"available": True, "up": False, "http_status_code": 502})
		)

		self.assertIn("unreachable", report["likely_cause"])
		self.assertIn("502", report["likely_cause"])

	def test_probe_http_5xx_flags_server_error(self):
		report = generate_report(
			self._base(site_uptime={"available": True, "up": True, "http_status_code": 503})
		)

		self.assertIn("503", report["likely_cause"])

	def test_probe_up_produces_no_uptime_cause(self):
		report = generate_report(
			self._base(site_uptime={"available": True, "up": True, "http_status_code": 200})
		)

		self.assertEqual(report["confidence"], "Low")

	def test_inactive_site_is_high_confidence_cause(self):
		payload = self._base()
		payload["site"]["status"] = "Suspended"
		report = generate_report(payload)

		self.assertIn("not Active", report["likely_cause"])
		self.assertIn("Suspended", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_inactive_bench_is_high_confidence_cause(self):
		report = generate_report(self._base(bench={"status": "Broken"}))

		self.assertIn("Bench is not Active", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_critical_usage_is_flagged_as_cause(self):
		payload = self._base()
		payload["site"]["usage_percent"] = {"disk": 130}
		report = generate_report(payload)

		self.assertIn("Disk usage is critically over quota", report["likely_cause"])

	def test_high_usage_is_evidence_not_a_cause(self):
		payload = self._base()
		payload["site"]["usage_percent"] = {"database": 95}
		report = generate_report(payload)

		self.assertTrue(any("high at 95%" in e for e in report["evidence"]))
		self.assertEqual(report["confidence"], "Low")

	def test_cancelled_site_update_is_high_confidence(self):
		report = generate_report(
			self._base(deployments=[{"name": "u1", "status": "Cancelled", "creation": "now"}])
		)

		self.assertIn("cancelled", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_in_progress_site_update_is_a_cause(self):
		report = generate_report(
			self._base(deployments=[{"name": "u1", "status": "Running", "creation": "now"}])
		)

		self.assertIn("in progress", report["likely_cause"])

	def test_failed_agent_jobs_are_high_confidence(self):
		report = generate_report(self._base(errors={"failed_job_count": 4, "window_hours": 24}))

		self.assertIn("agent jobs are failing", report["likely_cause"])
		self.assertEqual(report["confidence"], "High")

	def test_broken_domains_are_flagged(self):
		report = generate_report(self._base(domains={"counts_by_status": {"Broken": 2}}))

		self.assertIn("DNS/TLS", report["likely_cause"])

	def test_failed_backup_adds_next_step_without_cause(self):
		report = generate_report(self._base(backups={"latest": {"status": "Failure"}, "recent": []}))

		self.assertTrue(any("backup health" in step for step in report["recommended_next_steps"]))
		self.assertEqual(report["confidence"], "Low")

	def test_stopped_worker_process_is_evidence_not_a_cause(self):
		report = generate_report(
			self._base(
				bench_processes={
					"available": True,
					"stopped_processes": [{"name": "frappe-bench-frappe-short-worker", "status": "Fatal"}],
				}
			)
		)

		self.assertTrue(any("background worker" in e for e in report["evidence"]))
		self.assertEqual(report["confidence"], "Low")

	def test_noisy_neighbor_share_is_surfaced_as_evidence(self):
		report = generate_report(
			self._base(
				app_server_metrics={
					"available": True,
					"has_data": True,
					"cpu": {"available": True, "peak": 90.0, "mean": 30.0, "spike_detected": True},
				},
				server_advanced_analytics={
					"available": True,
					"target_site_rank": 4,
					"target_site_share_percent": 5.0,
					"site_count": 12,
				},
			)
		)

		self.assertTrue(any("ranks #4 of 12" in e for e in report["evidence"]))

	def test_generic_web_error_surfaces_exception_message(self):
		report = generate_report(
			self._base(
				web_error_log={
					"available": True,
					"error_count": 1,
					"recent_errors": [
						{"level": "error", "description": "boom", "exception": "ValueError: nope"}
					],
				}
			)
		)

		self.assertIn("ValueError: nope", report["likely_cause"])
