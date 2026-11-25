# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.backup_restoration_test.backup_test import BackupTest
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.server.test_server import create_test_server


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
