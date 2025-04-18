# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
import typing
import unittest
from unittest.mock import Mock, patch

import frappe
import responses
from frappe.model.naming import make_autoname

from press.exceptions import InsufficientSpaceOnServer
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.remote_file.remote_file import RemoteFile
from press.press.doctype.remote_file.test_remote_file import (
	create_test_remote_file,
)
from press.press.doctype.server.server import BaseServer, Server
from press.press.doctype.site.site import Site, process_rename_site_job_update
from press.telegram_utils import Telegram
from press.utils import get_current_team

if typing.TYPE_CHECKING:
	from datetime import datetime

	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.release_group.release_group import ReleaseGroup


def create_test_bench(
	user: str | None = None,
	group: ReleaseGroup = None,
	server: str | None = None,
	apps: list[dict] | None = None,
	creation: datetime | None = None,
	public_server: bool = False,
) -> "Bench":
	"""
	Create test Bench doc.

	API call to agent will be faked when creating the doc.
	"""
	from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
	from press.press.doctype.server.test_server import create_test_server

	creation = creation or frappe.utils.now_datetime()
	user = user or frappe.session.user
	if not server:
		proxy_server = create_test_proxy_server()
		database_server = create_test_database_server()
		server = create_test_server(proxy_server.name, database_server.name, public=public_server).name

	if not group:
		app = create_test_app()
		group = create_test_release_group([app], user)

	name = frappe.mock("name")
	candidate = group.create_deploy_candidate()
	candidate.db_set("docker_image", frappe.mock("url"))
	bench = frappe.get_doc(
		{
			"name": f"Test Bench{name}",
			"doctype": "Bench",
			"status": "Active",
			"background_workers": 1,
			"gunicorn_workers": 2,
			"group": group.name,
			"apps": apps,
			"candidate": candidate.name,
			"server": server,
		}
	).insert(ignore_if_duplicate=True)
	bench.db_set("creation", creation)
	bench.reload()
	return bench


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
def create_test_site(
	subdomain: str = "",
	new: bool = False,
	creation: datetime | None = None,
	bench: str | None = None,
	server: str | None = None,
	team: str | None = None,
	standby_for: str | None = None,
	apps: list[str] | None = None,
	remote_database_file=None,
	remote_public_file=None,
	remote_private_file=None,
	remote_config_file=None,
	**kwargs,
) -> Site:
	"""Create test Site doc.

	Installs all apps present in bench.
	"""
	creation = creation or frappe.utils.now_datetime()
	subdomain = subdomain or make_autoname("test-site-.#####")
	apps = [{"app": app} for app in apps] if apps else None
	if not bench:
		bench = create_test_bench(server=server, public_server=kwargs.get("public_server", False))
	else:
		bench = frappe.get_doc("Bench", bench)
	group = frappe.get_doc("Release Group", bench.group)

	status = "Pending" if new else "Active"
	# on_update checks won't be triggered if not Active

	site = frappe.get_doc(
		{
			"doctype": "Site",
			"status": status,
			"subdomain": subdomain,
			"server": bench.server,
			"bench": bench.name,
			"team": team or get_current_team(),
			"apps": apps or [{"app": app.app} for app in group.apps],
			"admin_password": "admin",
			"standby_for": standby_for,
			"remote_database_file": remote_database_file,
			"remote_public_file": remote_public_file,
			"remote_private_file": remote_private_file,
			"remote_config_file": remote_config_file,
		}
	)
	site.update(kwargs)
	site.insert()
	site.db_set("creation", creation)
	site.reload()
	return site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def setUp(self):
		frappe.db.truncate("Agent Request Failure")

	def tearDown(self):
		frappe.db.rollback()

	def test_host_name_updates_perform_checks_on_host_name(self):
		"""Ensure update of host name triggers verification of host_name."""
		site = create_test_site("testsubdomain")
		site.host_name = "balu.codes"  # domain that doesn't exist
		self.assertRaises(frappe.exceptions.ValidationError, site.save)

	def test_site_has_default_site_domain_on_create(self):
		"""Ensure site has default site domain on create."""
		site = create_test_site("testsubdomain")
		self.assertEqual(site.name, site.host_name)
		self.assertTrue(frappe.db.exists("Site Domain", {"domain": site.name}))

	def test_new_sites_set_host_name_in_site_config(self):
		"""Ensure new sites set host_name in site config in f server."""
		with patch.object(Site, "_update_configuration") as mock_update_config:
			site = create_test_site("testsubdomain", new=True)
		mock_update_config.assert_called_with({"host_name": f"https://{site.name}"}, save=False)

	def test_rename_updates_name(self):
		"""Ensure rename changes name of site."""
		domain = frappe.db.get_single_value("Press Settings", "domain")
		site = create_test_site("old-name")
		new_name = f"new-name.{domain}"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)

		self.assertFalse(frappe.db.exists("Site", {"name": f"old-name.{domain}"}))
		self.assertTrue(frappe.db.exists("Site", {"name": new_name}))

	def test_rename_creates_2_agent_jobs(self):
		"""Ensure rename creates 2 agent jobs (for f & n)."""
		domain = frappe.db.get_single_value("Press Settings", "domain")
		site = create_test_site("old-name")
		new_name = f"new-name.{domain}"

		rename_jobs_count_before = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_before = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		site.rename(new_name)

		rename_jobs_count_after = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_after = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		self.assertEqual(rename_jobs_count_after - rename_jobs_count_before, 1)
		self.assertEqual(rename_upstream_jobs_count_after - rename_upstream_jobs_count_before, 1)

	def test_subdomain_update_renames_site(self):
		"""Ensure updating subdomain renames site."""
		site = create_test_site("old-name")
		new_subdomain_name = "new-name"

		rename_jobs_count_before = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_before = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		site.subdomain = new_subdomain_name
		site.save()

		rename_jobs_count_after = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_after = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		self.assertEqual(rename_jobs_count_after - rename_jobs_count_before, 1)
		self.assertEqual(rename_upstream_jobs_count_after - rename_upstream_jobs_count_before, 1)

	def _fake_succeed_rename_jobs(self):
		rename_step_name_map = {
			"Rename Site": "Rename Site",
			"Rename Site on Upstream": "Rename Site File in Upstream Directory",
		}
		rename_job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site on Upstream"})
		frappe.db.set_value(
			"Agent Job Step",
			{
				"step_name": rename_step_name_map[rename_job.job_type],
				"agent_job": rename_job.name,
			},
			"status",
			"Success",
		)
		frappe.db.set_value(
			"Agent Job Step",
			{
				"step_name": rename_step_name_map[rename_upstream_job.job_type],
				"agent_job": rename_upstream_job.name,
			},
			"status",
			"Success",
		)
		return rename_job

	def test_default_domain_is_renamed_along_with_site(self):
		"""Ensure default domains are renamed when site is renamed."""
		site = create_test_site("old-name")
		old_name = site.name
		new_name = "new-name.fc.dev"

		self.assertTrue(frappe.db.exists("Site Domain", site.name))
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)

		self.assertFalse(frappe.db.exists("Site Domain", old_name))
		self.assertTrue(frappe.db.exists("Site Domain", new_name))

	def test_site_becomes_active_after_successful_rename(self):
		"""Ensure site becomes active after successful rename."""
		site = create_test_site("old-name")
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)

		site = frappe.get_doc("Site", new_name)
		self.assertEqual(site.status, "Active")

	@patch.object(Site, "rename")
	def test_rename_site_not_called_for_new_site(self, mock_rename):
		"""Rename Site job isn't created for new site."""
		create_test_site("some-name", new=True)
		mock_rename.assert_not_called()

	def test_site_rename_update_site_config(self):
		"""Ensure site configuration child table is updated after rename."""
		site = create_test_site("old-name")
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)
		site = frappe.get_doc("Site", new_name)
		if site.configuration[0].key == "host_name":
			config_host = site.configuration[0].value
		self.assertEqual(config_host, f"https://{new_name}")

	def test_no_new_jobs_after_rename(self):
		"""Ensure no new jobs are created after rename."""
		site = create_test_site("old-name")
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		job_count_before = frappe.db.count("Agent Job")
		process_rename_site_job_update(rename_job)
		job_count_after = frappe.db.count("Agent Job")
		self.assertEqual(job_count_before, job_count_after)

	def test_add_domain_to_config_adds_domains_key_to_site_configuration(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"

		site.add_domain_to_config(domain)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertIn(domain, domains)

	def test_add_domain_to_config_updates_config_for_existing_domains_key(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"
		domain_2 = "prod2.frappe.dev"
		site._update_configuration({"domains": [domain]})

		site.add_domain_to_config(domain_2)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertIn(domain, domains)
		self.assertIn(domain_2, domains)

	def test_add_remove_domain_from_config_updates_domains_key(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"
		domain_2 = "prod2.frappe.dev"
		site._update_configuration({"domains": [domain, domain_2]})

		site.remove_domain_from_config(domain)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertNotIn(domain, domains)
		self.assertIn(domain_2, domains)

	def test_site_rename_doesnt_update_host_name_for_custom_domain(self):
		"""Ensure site configuration isn't updated after rename when custom domain is host_name."""
		from press.press.doctype.site_domain.test_site_domain import create_test_site_domain

		site = create_test_site("old-name")
		site_domain1 = create_test_site_domain(site.name, "sitedomain1.com")
		site.set_host_name(site_domain1.name)
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)
		site = frappe.get_doc("Site", new_name)
		if site.configuration[0].key == "host_name":
			config_host = site.configuration[0].value
		self.assertEqual(config_host, f"https://{site_domain1.name}")

	def test_suspend_without_reload_creates_agent_job_with_skip_reload(self):
		site = create_test_site("testsubdomain")
		site.suspend(skip_reload=True)

		job = frappe.get_doc("Agent Job", {"site": site.name})
		self.assertTrue(json.loads(job.request_data).get("skip_reload"))

	def test_suspend_without_skip_reload_creates_agent_job_without_skip_reload(self):
		site = create_test_site("testsubdomain")
		site.suspend()

		job = frappe.get_doc("Agent Job", {"site": site.name})
		self.assertFalse(json.loads(job.request_data).get("skip_reload"))

	def test_archive_with_skip_reload_creates_agent_job_with_skip_reload(self):
		site = create_test_site("testsubdomain")
		site.archive(skip_reload=True)

		job = frappe.get_doc("Agent Job", {"site": site.name})
		self.assertTrue(json.loads(job.request_data).get("skip_reload"))

	def test_archive_without_skip_reload_creates_agent_job_without_skip_reload(self):
		site = create_test_site("testsubdomain")
		site.archive()

		job = frappe.get_doc("Agent Job", {"site": site.name})
		self.assertFalse(json.loads(job.request_data).get("skip_reload"))

	@patch.object(RemoteFile, "download_link", new="http://test.com")
	@patch.object(RemoteFile, "get_content", new=lambda x: {"a": "test"})  # type: ignore
	def test_new_site_with_backup_files(self):
		# no asserts here, just checking if it doesn't fail
		database = create_test_remote_file().name
		public = create_test_remote_file().name
		private = create_test_remote_file().name
		config = create_test_remote_file().name
		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="Site",
			interval="Daily",
			price_usd=30,
			price_inr=30,
			period=30,
		).insert()
		create_test_site(
			"test-site-restore",
			remote_database_file=database,
			remote_public_file=public,
			remote_private_file=private,
			remote_config_file=config,
			subscription_plan=plan.name,
		)

	@patch.object(Telegram, "send", new=Mock())
	@patch.object(BaseServer, "disk_capacity", new=Mock(return_value=100))
	@patch.object(RemoteFile, "download_link", new="http://test.com")
	@patch.object(RemoteFile, "get_content", new=lambda _: {"a": "test"})
	@patch.object(RemoteFile, "exists", lambda _: True)
	@patch.object(BaseServer, "increase_disk_size")
	@patch.object(BaseServer, "create_subscription_for_storage", new=Mock())
	def test_restore_site_adds_storage_if_no_sufficient_storage_available_on_public_server(
		self, mock_increase_disk_size: Mock
	):
		"""Ensure restore site adds storage if no sufficient storage available."""
		site = create_test_site()
		site.remote_database_file = create_test_remote_file(file_size=1024).name
		site.remote_public_file = create_test_remote_file(file_size=1024).name
		site.remote_private_file = create_test_remote_file(file_size=1024).name
		db_server = frappe.get_value("Server", site.server, "database_server")

		frappe.db.set_value("Server", site.server, "public", True)
		frappe.db.set_value(
			"Database Server",
			db_server,
			"public",
			True,
		)
		with patch.object(BaseServer, "free_space", new=Mock(return_value=500 * 1024 * 1024 * 1024)):
			site.restore_site()
		mock_increase_disk_size.assert_not_called()

		with patch.object(BaseServer, "free_space", new=Mock(return_value=0)):
			site.restore_site()
		mock_increase_disk_size.assert_called()

		frappe.db.set_value("Server", site.server, "public", False)
		frappe.db.set_value(
			"Database Server",
			db_server,
			"public",
			False,
		)
		with patch.object(Server, "free_space", new=Mock(return_value=0)):
			self.assertRaises(InsufficientSpaceOnServer, site.restore_site)

	def test_user_cannot_disable_auto_update_if_site_in_public_release_group(self):
		rg = create_test_release_group([create_test_app()], public=True)
		bench = create_test_bench(group=rg)
		site = create_test_site("testsite", bench=bench)
		site.skip_auto_updates = True
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			site.save(ignore_permissions=True)
		self.assertTrue(
			"Auto updates can't be disabled for sites on public benches" in str(context.exception)
		)

	def test_user_can_disable_auto_update_if_site_in_private_bench(self):
		rg = create_test_release_group([create_test_app()], public=False)
		bench = create_test_bench(group=rg)
		site = create_test_site("testsite", bench=bench)
		site.skip_auto_updates = True
		site.save(ignore_permissions=True)

	@responses.activate
	@patch.object(AppSource, "validate_dependant_apps", new=Mock())
	def test_sync_apps_updates_apps_child_table(self):
		app1 = create_test_app()
		app2 = create_test_app("erpnext", "ERPNext")
		group = create_test_release_group([app1, app2])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench)
		responses.get(
			f"https://{site.server}:443/agent/benches/{site.bench}/sites/{site.name}/apps",
			json.dumps({"data": "frappe\nerpnext"}),
		)
		site.sync_apps()
		self.assertEqual(site.apps[0].app, "frappe")
		self.assertEqual(site.apps[1].app, "erpnext")
		self.assertEqual(len(site.apps), 2)

	def test_delete_multiple_config_creates_job_to_remove_multiple_site_config_keys(self):
		site = create_test_site()
		site._set_configuration(
			[
				{"key": "key1", "value": "value1", "type": "String"},
				{"key": "key2", "value": "value2", "type": "String"},
			]
		)
		site.delete_multiple_config(["key1", "key2"])
		update_job = frappe.get_last_doc(
			"Agent Job", {"job_type": "Update Site Configuration", "site": site.name}
		)
		self.assertEqual(
			json.loads(update_job.request_data).get("remove"),
			["key1", "key2"],
		)

	def test_apps_are_reordered_to_follow_bench_order(self):
		app1 = create_test_app()
		app2 = create_test_app("erpnext", "ERPNext")
		app3 = create_test_app("crm", "Frappe CRM")
		group = create_test_release_group([app1, app2, app3])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name, apps=["frappe", "crm", "erpnext"])
		site.reload()
		self.assertEqual(site.apps[0].app, "frappe")
		self.assertEqual(site.apps[1].app, "erpnext")
		self.assertEqual(site.apps[2].app, "crm")
