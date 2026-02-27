# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
import typing
from unittest.mock import Mock, patch

import frappe
import frappe.utils
import responses
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.exceptions import InsufficientSpaceOnServer
from press.press.doctype.agent_job.agent_job import AgentJob, poll_pending_jobs
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.bench.bench import Bench
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.remote_file.remote_file import RemoteFile
from press.press.doctype.remote_file.test_remote_file import (
	create_test_remote_file,
)
from press.press.doctype.server.server import BaseServer, Server
from press.press.doctype.site.site import (
	ARCHIVE_AFTER_SUSPEND_DAYS,
	Site,
	archive_suspended_sites,
	process_rename_site_job_update,
	suspend_sites_exceeding_disk_usage_for_last_14_days,
)
from press.press.doctype.site_activity.test_site_activity import create_test_site_activity
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.saas.doctype.saas_settings.test_saas_settings import create_test_saas_settings
from press.utils import get_current_team

if typing.TYPE_CHECKING:
	from datetime import datetime

	from press.press.doctype.release_group.release_group import ReleaseGroup


@patch.object(DeployCandidateBuild, "pre_build", new=Mock())
def create_test_bench(
	user: str | None = None,
	group: ReleaseGroup | None = None,
	server: str | None = None,
	apps: list[dict] | None = None,
	creation: datetime | None = None,
	public_server: bool = False,
) -> Bench:
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
	deploy_candidate_build = candidate.build()
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
			"build": deploy_candidate_build["message"],
			"server": server,
			"docker_image": frappe.mock("url"),
		}
	).insert(ignore_if_duplicate=True)
	bench.db_set("creation", creation)
	bench.reload()
	return bench


@patch.object(Site, "sync_apps", new=Mock())
def create_test_site(
	subdomain: str = "",
	new: bool = False,
	creation: datetime | None = None,
	bench: str | None = None,
	server: str | None = None,
	team: str | None = None,
	standby_for_product: str | None = None,
	apps: list[str] | None = None,
	remote_database_file=None,
	remote_public_file=None,
	remote_private_file=None,
	remote_config_file=None,
	fake_agent_jobs: bool = False,
	**kwargs,
) -> Site:
	"""Create test Site doc.

	Installs all apps present in bench.
	"""
	from press.press.doctype.agent_job.test_agent_job import fake_agent_job

	if fake_agent_jobs:
		context = fake_agent_job(
			{
				"New Site": {"status": "Success"},
				"Update Site Configuration": {"status": "Success"},
				"Add Site to Upstream": {"status": "Success"},
			}
		)

	else:
		context = patch.object(AgentJob, "enqueue_http_request", new=Mock())

	with context:
		creation = creation or frappe.utils.now_datetime()
		subdomain = subdomain or make_autoname("test-site-.#####")
		apps_li_di: list[dict] | None = [{"app": app} for app in apps] if apps else None
		if not bench:
			bench_doc = create_test_bench(server=server, public_server=kwargs.get("public_server", False))
		else:
			bench_doc = Bench("Bench", bench)
		group = frappe.get_doc("Release Group", bench_doc.group)

		status = "Pending" if new else "Active"
		# on_update checks won't be triggered if not Active

		site = frappe.get_doc(
			{
				"doctype": "Site",
				"status": status,
				"subdomain": subdomain,
				"server": bench_doc.server,
				"bench": bench_doc.name,
				"team": team or get_current_team(),
				"apps": apps_li_di or [{"app": app.app} for app in group.apps],
				"admin_password": "admin",
				"standby_for_product": standby_for_product,
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
		if fake_agent_jobs:
			poll_pending_jobs()
			site.reload()
		return site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestSite(FrappeTestCase):
	"""Tests for Site Document methods."""

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

	@patch.object(TelegramMessage, "enqueue", new=Mock())
	@patch.object(BaseServer, "disk_capacity", new=Mock(return_value=100))
	@patch.object(RemoteFile, "download_link", new="http://test.com")
	@patch.object(RemoteFile, "get_content", new=lambda _: {"a": "test"})
	@patch.object(RemoteFile, "exists", lambda _: True)
	@patch.object(BaseServer, "calculated_increase_disk_size")
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
		site = create_test_site("testsite", bench=bench.name)
		site.skip_auto_updates = True
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			site.save(ignore_permissions=True)
		self.assertTrue(
			"Auto updates can't be disabled for sites on public benches" in str(context.exception)
		)

	def test_user_can_disable_auto_update_if_site_in_private_bench(self):
		rg = create_test_release_group([create_test_app()], public=False)
		bench = create_test_bench(group=rg)
		site = create_test_site("testsite", bench=bench.name)
		site.skip_auto_updates = True
		site.save(ignore_permissions=True)

	@responses.activate
	@patch.object(AppSource, "validate_dependent_apps", new=Mock())
	def test_sync_apps_updates_apps_child_table(self):
		app1 = create_test_app()
		app2 = create_test_app("erpnext", "ERPNext")
		group = create_test_release_group([app1, app2])
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)
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

	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.rollback", new=Mock())
	def test_archive_suspended_sites_archives_only_sites_with_backup_suspended_longer_than_days(self):
		offsite_backup_plan = create_test_plan(
			"Site", price_usd=5.0, price_inr=375.0, plan_name="Offsite Backup plan", offsite_backups=True
		)
		site = create_test_site(plan=offsite_backup_plan.name)
		site.db_set("status", "Suspended")
		site_activity = create_test_site_activity(site.name, "Suspend Site")
		site_activity.db_set(
			"creation", frappe.utils.add_days(frappe.utils.now_datetime(), -ARCHIVE_AFTER_SUSPEND_DAYS - 1)
		)
		site2 = create_test_site(plan=offsite_backup_plan.name)
		site2.db_set("status", "Suspended")
		site2_activity = create_test_site_activity(site2.name, "Suspend Site")
		site2_activity.db_set(
			"creation", frappe.utils.add_days(frappe.utils.now_datetime(), -ARCHIVE_AFTER_SUSPEND_DAYS + 1)
		)  # site2 suspended recently
		site3 = create_test_site(plan=offsite_backup_plan.name)  # active site should not be archived

		create_test_saas_settings(None, [create_test_app(), create_test_app("erpnext", "ERPNext")])

		archive_suspended_sites()
		site.reload()
		site2.reload()
		site3.reload()
		self.assertEqual(site.status, "Pending")  # to be archived
		self.assertEqual(site2.status, "Suspended")
		self.assertEqual(site3.status, "Active")

	@patch("press.press.doctype.site.site.frappe.db.commit", new=Mock())
	@patch("press.press.doctype.site.site.frappe.db.rollback", new=Mock())
	def test_suspension_of_no_offsite_backup_site_triggers_backup_if_it_does_not_exist(self):
		plan_10 = create_test_plan(
			"Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10", offsite_backups=False
		)

		site = create_test_site()
		site.db_set("status", "Suspended")
		site.db_set("plan", plan_10.name)
		site_activity = create_test_site_activity(site.name, "Suspend Site")
		site_activity.db_set(
			"creation", frappe.utils.add_days(frappe.utils.now_datetime(), -ARCHIVE_AFTER_SUSPEND_DAYS - 1)
		)

		site2 = create_test_site()
		site2.db_set("status", "Suspended")
		site2.db_set("plan", plan_10.name)
		site2_activity = create_test_site_activity(site2.name, "Suspend Site")
		site2_activity.db_set(
			"creation", frappe.utils.add_days(frappe.utils.now_datetime(), -ARCHIVE_AFTER_SUSPEND_DAYS - 1)
		)
		from press.press.doctype.site_backup.test_site_backup import create_test_site_backup

		create_test_site_backup(site2.name)

		create_test_saas_settings(None, [create_test_app(), create_test_app("erpnext", "ERPNext")])

		self.assertEqual(frappe.db.count("Site Backup", {"site": site.name, "status": "Pending"}), 0)
		self.assertEqual(frappe.db.count("Site Backup", {"site": site2.name, "status": "Pending"}), 0)
		archive_suspended_sites()
		self.assertEqual(frappe.db.count("Site Backup", {"site": site.name, "status": "Pending"}), 1)
		self.assertEqual(frappe.db.count("Site Backup", {"site": site2.name, "status": "Pending"}), 0)

		site.reload()
		site2.reload()

		self.assertNotEqual(site.status, "Pending")  # should not be archived
		self.assertEqual(site2.status, "Pending")

	def test_site_usage_exceed_tracking(self):
		team = create_test_team()
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		site = create_test_site(plan=plan_10.name, public_server=True, team=team.name)

		self.assertEqual(site.status, "Active")
		self.assertFalse(site.site_usage_exceeded)

		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded()
		site.reload()

		self.assertTrue(site.site_usage_exceeded)
		self.assertIsNotNone(site.site_usage_exceeded_on)
		self.assertEqual(site.status, "Active")

	def test_free_sites_ignore_usage_exceed_tracking(self):
		team = create_test_team(free_account=False)
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		site = create_test_site(plan=plan_10.name, public_server=True, team=team.name, free=True)

		self.assertEqual(site.status, "Active")
		self.assertFalse(site.site_usage_exceeded)

		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded()
		site.reload()

		self.assertFalse(site.site_usage_exceeded)
		self.assertIsNone(site.site_usage_exceeded_on)
		self.assertEqual(site.status, "Active")

	def test_free_team_sites_ignore_usage_exceed_tracking(self):
		team = create_test_team(free_account=True)
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		site = create_test_site(plan=plan_10.name, public_server=True, team=team.name, free=False)

		self.assertEqual(site.status, "Active")
		self.assertFalse(site.site_usage_exceeded)

		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded()
		site.reload()

		self.assertFalse(site.site_usage_exceeded)
		self.assertIsNone(site.site_usage_exceeded_on)

	def test_sites_on_dedicated_server_ignore_usage_exceed_tracking(self):
		team = create_test_team()
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		site = create_test_site(plan=plan_10.name, public_server=False, team=team.name)

		self.assertEqual(site.status, "Active")
		self.assertFalse(site.site_usage_exceeded)

		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded()
		site.reload()

		self.assertFalse(site.site_usage_exceeded)
		self.assertIsNone(site.site_usage_exceeded_on)
		self.assertEqual(site.status, "Active")

	def test_reset_disk_usage_exceed_alert_on_changing_plan(self):
		team = create_test_team()
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		plan_20 = create_test_plan("Site", price_usd=20.0, price_inr=1500.0, plan_name="USD 20")

		site: Site = create_test_site(plan=plan_10.name, public_server=True, team=team.name)
		site.create_subscription(plan=plan_10.name)
		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded(save=True)
		site.reload()

		self.assertTrue(site.site_usage_exceeded)

		site.change_plan(plan_20.name, ignore_card_setup=True)
		site.reload()

		self.assertFalse(site.site_usage_exceeded)
		self.assertIsNone(site.site_usage_exceeded_on)

	def test_reset_disk_usage_exceed_alert_on_reducing_disk_size(self):
		team = create_test_team()
		plan_10 = create_test_plan("Site", price_usd=10.0, price_inr=750.0, plan_name="USD 10")
		site: Site = create_test_site(plan=plan_10.name, public_server=True, team=team.name)
		site.create_subscription(plan=plan_10.name)
		site.current_disk_usage = 150
		site.check_if_disk_usage_exceeded(save=True)
		site.reload()

		self.assertTrue(site.site_usage_exceeded)

		site.current_disk_usage = 50
		site.check_if_disk_usage_exceeded(save=True)
		site.reload()

		self.assertFalse(site.site_usage_exceeded)
		self.assertIsNone(site.site_usage_exceeded_on)

	@patch("frappe.sendmail", new=Mock())
	def test_suspend_site_on_exceeding_site_usage_for_consecutive_14_days(self):
		frappe.db.set_single_value("Press Settings", "enforce_storage_limits", 1)
		team = create_test_team()
		site: Site = create_test_site(public_server=True, free=False, team=team.name)

		site.current_database_usage = 150
		site.site_usage_exceeded = True
		site.site_usage_exceeded_on = frappe.utils.add_to_date(None, days=-2)
		site.save()
		self.assertEqual(site.status, "Active")

		suspend_sites_exceeding_disk_usage_for_last_14_days()
		site.reload()
		self.assertEqual(site.status, "Active")

		site.site_usage_exceeded_on = frappe.utils.add_to_date(None, days=-6)
		site.save()
		suspend_sites_exceeding_disk_usage_for_last_14_days()
		site.reload()
		self.assertEqual(site.status, "Active")

		site.site_usage_exceeded_on = frappe.utils.add_to_date(None, days=-7)
		site.save()
		suspend_sites_exceeding_disk_usage_for_last_14_days()
		site.reload()
		self.assertEqual(site.status, "Active")

		site.site_usage_exceeded_on = frappe.utils.add_to_date(None, days=-15)
		site.save()
		suspend_sites_exceeding_disk_usage_for_last_14_days()
		site.reload()
		self.assertEqual(site.status, "Suspended")
