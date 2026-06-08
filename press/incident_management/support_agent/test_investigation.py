from __future__ import annotations

import sys
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

# frappe_mcp is not installed in test environments; stub it so that
# press.mcp.tools.telemetry.clients can be imported when patching starts.
sys.modules.setdefault("frappe_mcp", MagicMock())

import frappe  # noqa: E402
from frappe.tests.utils import FrappeTestCase  # noqa: E402

from press.incident_management.support_agent.collectors import collect_site_context  # noqa: E402
from press.incident_management.support_agent.report import generate_report  # noqa: E402

_SITE_NAME = "test.frappe.cloud"
_BENCH_NAME = "test-bench-001"
_SERVER_NAME = "server.frappe.cloud"
_DB_SERVER_NAME = "db.frappe.cloud"

_SITE_DATA = frappe._dict(
	{
		"name": _SITE_NAME,
		"status": "Active",
		"bench": _BENCH_NAME,
		"server": _SERVER_NAME,
		"database_server": _DB_SERVER_NAME,
		"cluster": "default",
		"group": "test-group",
		"archive_failed": 0,
		"creation_failed": None,
		"suspended_at": None,
		"is_monitoring_disabled": 0,
		"setup_wizard_complete": 1,
		"current_cpu_usage": 50,
		"current_database_usage": 30,
		"current_disk_usage": 20,
	}
)

_BENCH_DATA = frappe._dict(
	{
		"name": _BENCH_NAME,
		"status": "Active",
		"server": _SERVER_NAME,
		"database_server": _DB_SERVER_NAME,
		"cluster": "default",
		"candidate": "candidate-001",
		"build": "build-001",
		"background_workers": 2,
		"gunicorn_workers": 4,
		"auto_scale_workers": 0,
		"use_rq_workerpool": 0,
		"merge_all_rq_queues": 0,
		"merge_default_and_short_rq_queues": 0,
		"last_inplace_update_failed": 0,
		"resetting_bench": 0,
	}
)

_PROM_EMPTY = {"status": "success", "data": {"resultType": "matrix", "result": []}}
_ES_EMPTY = {"aggregations": {"top": {"buckets": []}}}


def _prometheus_series(values: list[float]) -> dict:
	"""Prometheus query_range matrix response with a single series."""
	return {
		"status": "success",
		"data": {
			"resultType": "matrix",
			"result": [
				{
					"metric": {},
					"values": [[1700000000 + i * 1800, str(v)] for i, v in enumerate(values)],
				}
			],
		},
	}


def _elasticsearch_endpoints(buckets: list[dict]) -> dict:
	"""Elasticsearch terms-aggregation response for slow endpoints."""
	return {
		"aggregations": {
			"top": {
				"buckets": [
					{
						"key": b["path"],
						"doc_count": 100,
						"avg_duration_ms": {"value": b["avg_ms"]},
						"max_duration_ms": {"value": b["max_ms"]},
					}
					for b in buckets
				]
			}
		}
	}


class TestSupportAgentInvestigation(FrappeTestCase):
	"""E2E tests: HTTP clients return controlled payloads; the full collect→report
	pipeline runs without DB records."""

	def _run(
		self,
		*,
		prometheus=None,
		elasticsearch=None,
		processes=None,
		web_log="",
	) -> dict:
		bench_doc = MagicMock()
		bench_doc.supervisorctl_status.return_value = processes if processes is not None else []

		site_doc = MagicMock()
		site_doc.get_server_log.return_value = {"web.error.log": web_log}

		def _mock_get_doc(doctype, name):
			if doctype == "Bench":
				return bench_doc
			if doctype == "Site":
				return site_doc
			return MagicMock()

		def _gsv(doctype, fieldname, *args, **kwargs):
			if doctype == "Press Settings" and fieldname == "monitor_server":
				return "fake-monitor.example.com"
			if doctype == "Press Settings" and fieldname == "log_server":
				return "fake-log.example.com"
			return None

		with ExitStack() as stack:
			stack.enter_context(
				patch(
					"press.incident_management.support_agent.collectors._get_site",
					return_value=_SITE_DATA,
				)
			)
			stack.enter_context(
				patch(
					"press.incident_management.support_agent.collectors.get_bench_health",
					return_value=_BENCH_DATA,
				)
			)
			stack.enter_context(patch("frappe.get_all", return_value=[]))
			stack.enter_context(patch("frappe.get_doc", side_effect=_mock_get_doc))
			stack.enter_context(patch.object(frappe.db, "get_single_value", side_effect=_gsv))
			stack.enter_context(
				patch(
					"press.mcp.tools.telemetry.clients.prometheus_get",
					return_value=prometheus or _PROM_EMPTY,
				)
			)
			stack.enter_context(
				patch(
					"press.mcp.tools.telemetry.clients.elasticsearch_post",
					return_value=elasticsearch or _ES_EMPTY,
				)
			)
			stack.enter_context(
				patch(
					"press.api.analytics.get_current_cpu_usage_for_sites_on_server",
					return_value={},
				)
			)
			payload = collect_site_context(_SITE_NAME)

		return generate_report(payload)

	def test_prometheus_cpu_spike_surfaces_app_server_cpu_cause(self):
		# Mean ~41%, peak 95% — ratio 2.3x > 1.5x threshold; peak > 70% threshold
		values = [40.0] * 40 + [95.0]

		report = self._run(prometheus=_prometheus_series(values))

		self.assertTrue(
			any("CPU" in e and "peak" in e.lower() for e in report["evidence"]),
			f"Expected CPU evidence, got: {report['evidence']}",
		)
		self.assertIn("CPU spiked", report["likely_cause"])

	def test_prometheus_flat_cpu_produces_no_cpu_cause(self):
		# Flat 30% — peak < 70% threshold so no spike
		values = [30.0] * 48

		report = self._run(prometheus=_prometheus_series(values))

		self.assertNotIn("CPU spiked", report["likely_cause"])

	def test_elasticsearch_uniformly_slow_endpoint_surfaces_web_worker_cause(self):
		# avg 5.2s, peak 9.8s — ratio 1.9x < 3x so not spiky; avg > 1s so slow
		elasticsearch = _elasticsearch_endpoints(
			[{"path": "/api/method/frappe.desk.reportview.get", "avg_ms": 5200.0, "max_ms": 9800.0}]
		)

		report = self._run(elasticsearch=elasticsearch)

		self.assertIn("web workers", report["likely_cause"])

	def test_elasticsearch_spiky_endpoint_surfaces_spike_evidence(self):
		# avg 400ms (0.4s), peak 18000ms (18s) — ratio 45x > 3x; peak > 2s
		elasticsearch = _elasticsearch_endpoints(
			[{"path": "/api/method/frappe.desk.query_report.run", "avg_ms": 400.0, "max_ms": 18000.0}]
		)

		report = self._run(elasticsearch=elasticsearch)

		self.assertTrue(
			any("spike" in e.lower() for e in report["evidence"]),
			f"Expected spike evidence, got: {report['evidence']}",
		)
		self.assertTrue(
			any("Recorder" in step for step in report["recommended_next_steps"]),
			report["recommended_next_steps"],
		)

	def test_supervisorctl_stopped_web_process_surfaces_502_cause(self):
		processes = [
			{
				"program": "frappe-bench-web:frappe-bench-frappe-web",
				"name": "frappe-bench-frappe-web",
				"status": "Fatal",
				"message": "Exited too quickly (process log may have details)",
				"group": "frappe-bench-web",
				"uptime": None,
				"uptime_string": None,
				"pid": None,
			}
		]

		report = self._run(processes=processes)

		self.assertIn("Gunicorn", report["likely_cause"])
		self.assertIn("502", report["likely_cause"])
		self.assertTrue(
			any("web.error.log" in step for step in report["recommended_next_steps"]),
			report["recommended_next_steps"],
		)

	def test_web_error_log_db_connectivity_surfaces_infra_cause(self):
		web_log = (
			"[2026-06-08 10:00:00 +0000] [1234] [ERROR] Error handling request\n"
			"OperationalError: (2003, \"Can't connect to MySQL server on '10.0.0.1' (111)\")\n"
		)

		report = self._run(web_log=web_log)

		self.assertIn("database connectivity", report["likely_cause"])
		self.assertTrue(
			any("database server" in step for step in report["recommended_next_steps"]),
			report["recommended_next_steps"],
		)
