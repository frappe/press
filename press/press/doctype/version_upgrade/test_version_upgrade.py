# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch
import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_update.test_site_update import create_test_site_update

from press.press.doctype.version_upgrade.version_upgrade import VersionUpgrade


def create_test_version_upgrade(site: str, destination_group: str) -> VersionUpgrade:
	return frappe.get_doc(
		dict(doctype="Version Upgrade", site=site, destination_group=destination_group)
	).insert(ignore_if_duplicate=True)


@patch.object(AgentJob, "enqueue_http_request", Mock())
class TestVersionUpgrade(FrappeTestCase):
	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_version_upgrade_creation_throws_when_destination_doesnt_have_all_apps_in_source(
		self,
	):
		server = create_test_server()
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")

		group1 = create_test_release_group([app1, app2, app3])
		group2 = create_test_release_group([app1])

		source_bench = create_test_bench(group=group1, server=server.name)
		create_test_bench(group=group2, server=server.name)

		site = create_test_site(bench=source_bench.name)
		site.install_app(app2.name)

		group2.add_server(server.name)

		self.assertRaisesRegex(
			frappe.ValidationError,
			f".*apps installed on {site.name}: app., app.$",
			create_test_version_upgrade,
			site.name,
			group2.name,
		)

	def test_version_upgrade_creates_site_update_even_when_past_updates_failed(self):
		server = create_test_server()
		app1 = create_test_app()  # frappe

		group1 = create_test_release_group([app1])
		group2 = create_test_release_group([app1])

		source_bench = create_test_bench(group=group1, server=server.name)
		create_test_bench(group=group2, server=server.name)

		site = create_test_site(bench=source_bench.name)

		group2.add_server(server.name)

		create_test_site_update(
			site.name, group2.name, "Recovered"
		)  # cause of failure not resolved
		site_updates_before = frappe.db.count("Site Update", {"site": site.name})
		version_upgrade = create_test_version_upgrade(site.name, group2.name)
		version_upgrade.start()  # simulate scheduled one. User will be admin
		site_updates_after = frappe.db.count("Site Update", {"site": site.name})
		self.assertEqual(site_updates_before + 1, site_updates_after)
