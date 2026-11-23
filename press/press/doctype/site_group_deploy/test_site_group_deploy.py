# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.server.test_server import create_test_server


class TestSiteGroupDeploy(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_optimal_server_for_private_bench_skips_server_excluded_from_scheduling(self):
		cluster = create_test_cluster(name="Excluded Test", region="eu-central-1", public=True).name
		server = create_test_server(cluster=cluster, public=True, provider="Hetzner").name
		frappe.db.set_value("Server", server, "exclude_for_scheduling", 1)

		deploy = frappe.get_doc({"doctype": "Site Group Deploy", "cluster": cluster, "provider": "Hetzner"})

		self.assertIsNone(deploy.get_optimal_server_for_private_bench())
