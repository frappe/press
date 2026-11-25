# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.backup_restoration_test.backup_test import BackupTest, run_backup_restore_test
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.remote_file.remote_file import RemoteFile
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup


class TestBackupRestorationTest(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_site_selection_skips_archived_clusters_and_unreachable_servers(self):
		"""One unreachable agent or a dead region must not stop the quarterly test."""
		live = create_test_server(public=True).name
		archived_cluster = create_test_cluster(name="Archived Region", region="me-south-1")
		frappe.db.set_value("Cluster", archived_cluster.name, "status", "Archived")
		archived = create_test_server(cluster=archived_cluster.name, public=True).name

		with patch(
			"press.press.doctype.backup_restoration_test.backup_test.get_benches_in_server",
			side_effect=Exception("502"),
		) as get_benches_in_server:
			BackupTest()

		called = [call.args[0] for call in get_benches_in_server.call_args_list]
		self.assertIn(live, called)
		self.assertNotIn(archived, called)

	@patch("press.press.doctype.backup_restoration_test.backup_test.send_raven_message")
	def test_raven_alert_mentions_owner_when_no_test_is_created(self, send_raven_message):
		create_test_server(public=True)

		with patch(
			"press.press.doctype.backup_restoration_test.backup_test.get_benches_in_server",
			side_effect=Exception("502"),
		):
			run_backup_restore_test()

		send_raven_message.assert_called_once()
		message = send_raven_message.call_args.args[0]
		self.assertIn("created 0 of 0 tests", message)
		self.assertIn('data-id="shadrak@erpnext.com"', message)

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	@patch.object(RemoteFile, "exists", new=Mock(return_value=True))
	@patch.object(RemoteFile, "download_link", new="http://test.com")
	@patch(
		"press.press.doctype.backup_restoration_test.backup_restoration_test.frappe.db.commit", new=MagicMock
	)
	def test_administrator_creates_test_site_on_a_server_of_another_team(self):
		"""The scheduler runs as Administrator, whose team does not own the public servers."""
		cluster = create_test_cluster("Default", public=True)
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		proxy = create_test_proxy_server(cluster=cluster.name, domain=root_domain.name)
		server = create_test_server(cluster=cluster.name, proxy_server=proxy.name, public=True)
		group = create_test_release_group([create_test_app()], public=True, servers=[server.name])
		bench = create_test_bench(group=group, server=server.name)
		site = create_test_site(bench=bench.name)
		create_test_site_backup(site.name)

		test = frappe.get_doc(
			{"doctype": "Backup Restoration Test", "site": site.name, "status": "Running"}
		).insert()

		self.assertTrue(test.test_site)
