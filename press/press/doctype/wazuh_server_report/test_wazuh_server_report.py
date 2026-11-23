# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.server import UNREGISTERED_WAZUH_AGENT_STATUS
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.wazuh_server_report.wazuh_server_report import WazuhServerReport, sync_wazuh_reports

MODULE = "press.press.doctype.wazuh_server_report.wazuh_server_report"

AGENT = {
	"id": "007",
	"name": "placeholder",
	"status": "active",
	"version": "Wazuh v4.14.6",
	"os": {"name": "Ubuntu"},
	"lastKeepAlive": "2026-11-04T10:00:00+00:00",
}
SCA_RESULTS = [
	{
		"policy_id": "cis_ubuntu22-04",
		"name": "CIS Ubuntu 22.04 Benchmark",
		"pass": 180,
		"fail": 20,
		"invalid": 2,
		"total_checks": 202,
		"score": 90,
		"end_scan": "2026-11-04T09:30:00+00:00",
	}
]
SEVERITY_COUNTS = {"Critical": 1, "High": 2, "Medium": 7, "Low": 11}


def finding(cve: str, package: str, severity: str = "High", version: str = "1.0") -> dict:
	return {
		"vulnerability": {
			"id": cve,
			"severity": severity,
			"score": {"base": 8.1},
			"detected_at": "2026-11-01T00:00:00+00:00",
			"published_at": "2026-10-01T00:00:00+00:00",
			"description": f"{cve} in {package}",
			"reference": f"https://nvd.nist.gov/vuln/detail/{cve}",
		},
		"package": {"name": package, "version": version},
	}


FINDINGS = [finding("CVE-2026-0001", "openssl", "Critical"), finding("CVE-2026-0002", "curl")]


class TestWazuhServerReport(FrappeTestCase):
	def setUp(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		self.server = str(create_test_server().name)
		frappe.db.set_value("Server", self.server, "is_wazuh_agent_installed", 1)

	def tearDown(self):
		frappe.db.rollback()

	def sync(self, agent=AGENT, sca_results=SCA_RESULTS, counts=SEVERITY_COUNTS, findings=FINDINGS):
		manager, indexer = Mock(), Mock()
		manager.get_agent.return_value = agent
		manager.sca_results.return_value = sca_results
		indexer.severity_counts.return_value = counts
		indexer.vulnerabilities.return_value = findings
		with (
			patch(f"{MODULE}.WazuhManager", return_value=manager),
			patch(f"{MODULE}.WazuhIndexer", return_value=indexer),
		):
			sync_wazuh_reports()
		return manager, indexer

	def report(self) -> WazuhServerReport:
		name = frappe.db.get_value("Wazuh Server Report", {"server": self.server})
		return WazuhServerReport("Wazuh Server Report", str(name))

	def vulnerabilities(self) -> dict[str, frappe._dict]:
		fields = ["cve", "package", "package_version", "severity", "status", "resolved_at", "last_seen"]
		return {
			row.cve: row for row in frappe.get_all("Wazuh Vulnerability", {"server": self.server}, fields)
		}

	def test_sync_records_agent_sca_policies_and_severity_counts_on_the_report(self):
		self.sync()

		report = self.report()
		self.assertEqual(report.agent_id, "007")
		self.assertEqual(report.agent_status, "active")
		self.assertEqual(report.operating_system, "Ubuntu")
		self.assertIsNotNone(report.last_keep_alive)
		self.assertEqual((report.vulnerabilities_critical, report.vulnerabilities_high), (1, 2))
		self.assertEqual((report.vulnerabilities_medium, report.vulnerabilities_low), (7, 11))
		self.assertEqual(len(report.sca_policies), 1)
		self.assertEqual(report.sca_policies[0].policy_name, "CIS Ubuntu 22.04 Benchmark")
		self.assertEqual((report.sca_policies[0].passed, report.sca_policies[0].failed), (180, 20))

	def test_sync_inserts_the_findings_as_active_vulnerabilities(self):
		self.sync()

		vulnerabilities = self.vulnerabilities()
		self.assertEqual(set(vulnerabilities), {"CVE-2026-0001", "CVE-2026-0002"})
		self.assertEqual(vulnerabilities["CVE-2026-0001"].severity, "Critical")
		self.assertEqual(vulnerabilities["CVE-2026-0001"].status, "Active")

	def test_second_sync_resolves_the_vulnerability_the_indexer_no_longer_lists(self):
		self.sync()
		self.sync(findings=[finding("CVE-2026-0002", "curl")])

		vulnerabilities = self.vulnerabilities()
		self.assertEqual(vulnerabilities["CVE-2026-0001"].status, "Resolved")
		self.assertIsNotNone(vulnerabilities["CVE-2026-0001"].resolved_at)
		self.assertEqual(vulnerabilities["CVE-2026-0002"].status, "Active")
		self.assertEqual(frappe.db.count("Wazuh Vulnerability", {"server": self.server}), 2)

	def test_second_sync_refreshes_the_package_version_of_an_active_vulnerability(self):
		self.sync()
		self.sync(findings=[finding("CVE-2026-0001", "openssl", "Critical", version="1.1")])

		self.assertEqual(self.vulnerabilities()["CVE-2026-0001"].package_version, "1.1")

	def test_a_cve_the_indexer_lists_twice_for_one_package_makes_one_row(self):
		twice = [
			finding("CVE-2026-0001", "openssl", version="1.0"),
			finding("CVE-2026-0001", "openssl", version="1.1"),
		]
		self.sync(findings=twice)
		self.sync(findings=twice)

		self.assertEqual(
			frappe.db.count("Wazuh Vulnerability", {"server": self.server, "cve": "CVE-2026-0001"}), 1
		)

	def test_an_extra_active_row_for_one_cve_and_package_is_resolved(self):
		self.sync()
		frappe.get_doc(
			{
				"doctype": "Wazuh Vulnerability",
				"server_type": "Server",
				"server": self.server,
				"cve": "CVE-2026-0001",
				"package": "openssl",
				"status": "Active",
			}
		).insert()
		self.sync()

		statuses = frappe.get_all(
			"Wazuh Vulnerability", {"server": self.server, "cve": "CVE-2026-0001"}, pluck="status"
		)
		self.assertEqual(sorted(statuses), ["Active", "Resolved"])

	def test_second_sync_updates_the_single_report_instead_of_adding_one(self):
		self.sync()
		self.sync(counts={"Critical": 0, "High": 1})

		self.assertEqual(frappe.db.count("Wazuh Server Report", {"server": self.server}), 1)
		self.assertEqual((self.report().vulnerabilities_critical, self.report().vulnerabilities_high), (0, 1))

	def test_unregistered_agent_clears_the_report_and_resolves_its_vulnerabilities(self):
		self.sync()
		_, indexer = self.sync(agent=None)

		report = self.report()
		self.assertEqual(report.agent_status, UNREGISTERED_WAZUH_AGENT_STATUS)
		self.assertIsNone(report.agent_id)
		self.assertEqual((report.vulnerabilities_critical, report.vulnerabilities_high), (0, 0))
		self.assertEqual(report.sca_policies, [])
		self.assertEqual({row.status for row in self.vulnerabilities().values()}, {"Resolved"})
		indexer.vulnerabilities.assert_not_called()

	def test_a_server_that_fails_after_its_report_is_saved_is_rolled_back_and_the_next_one_synced(self):
		other = str(create_test_server().name)
		frappe.db.set_value("Server", other, "is_wazuh_agent_installed", 1)
		manager, indexer = Mock(), Mock()
		manager.get_agent.return_value = AGENT
		manager.sca_results.return_value = SCA_RESULTS
		indexer.severity_counts.return_value = SEVERITY_COUNTS
		indexer.vulnerabilities.side_effect = lambda name: [] if name == other else 1 / 0

		with (
			patch(f"{MODULE}.WazuhManager", return_value=manager),
			patch(f"{MODULE}.WazuhIndexer", return_value=indexer),
			patch(f"{MODULE}.log_error") as log_error,
		):
			sync_wazuh_reports()

		self.assertTrue(frappe.db.exists("Wazuh Server Report", {"server": other}))
		self.assertFalse(frappe.db.exists("Wazuh Server Report", {"server": self.server}))
		self.assertEqual(log_error.call_args.kwargs["server"], self.server)

	def test_sync_fails_once_when_the_manager_is_unreachable(self):
		manager = Mock()
		manager.authenticate.side_effect = ConnectionError("manager down")
		with (
			patch(f"{MODULE}.WazuhManager", return_value=manager),
			patch(f"{MODULE}.WazuhIndexer"),
			patch(f"{MODULE}.log_error") as log_error,
			self.assertRaisesRegex(ConnectionError, "manager down"),
		):
			sync_wazuh_reports()
		log_error.assert_not_called()

	def test_sync_does_nothing_when_the_wazuh_api_is_not_configured(self):
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "")
		with patch(f"{MODULE}.WazuhManager") as manager:
			sync_wazuh_reports()
		manager.assert_not_called()
