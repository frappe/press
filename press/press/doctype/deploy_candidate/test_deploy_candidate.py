# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import random
import typing
from unittest import skip
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import (
	create_test_press_admin_team,
	create_test_team,
)
from press.utils.test import foreground_enqueue_doc

if typing.TYPE_CHECKING:
	from typing import TypedDict

	from press.press.doctype.app.app import App
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.team.team import Team

	class AppInfo(TypedDict):
		app: App
		source: AppSource
		release: AppRelease


def create_test_deploy_candidate(group: ReleaseGroup) -> DeployCandidate:
	"""
	Create Test Deploy Candidate doc
	"""
	return group.create_deploy_candidate()


def create_test_deploy_candidate_build(
	deploy_candidate: DeployCandidate,
	no_build: bool = False,
	no_push: bool = False,
	no_cache: bool = False,
	status: str = "Pending",
) -> DeployCandidateBuild:
	deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
		{
			"doctype": "Deploy Candidate Build",
			"deploy_candidate": deploy_candidate.name,
			"no_build": no_build,
			"no_push": no_push,
			"no_cache": no_cache,
			"group": deploy_candidate.group,
			"status": status,
		}
	)
	return deploy_candidate_build


@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestDeployCandidate(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_press_admin_team()
		self.user: str = self.team.user

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	@patch.object(DeployCandidateBuild, "_build", new=Mock())
	def test_if_new_press_admin_team_can_pre_build(self, mock_enqueue_doc, mock_commit):
		"""
		Test if new press admin team user can pre build

		Checks permission. Make sure no PermissionError is raised
		"""
		app = create_test_app()
		group = create_test_release_group([app], self.user)
		group.db_set("team", self.team.name)
		frappe.set_user(self.user)
		deploy_candidate = create_test_deploy_candidate(group)
		deploy_candidate_build = create_test_deploy_candidate_build(deploy_candidate, no_build=True)
		try:
			deploy_candidate_build.insert()
		except frappe.PermissionError:
			self.fail("PermissionError raised in pre_build")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	@patch.object(DeployCandidateBuild, "_build", new=Mock())
	def test_old_style_press_admin_team_can_pre_build(self, mock_enqueue_doc, mock_commit):
		"""
		Test if old style press admin team can pre build

		Checks permission. Make sure no PermissionError is raised
		"""
		app = create_test_app()
		group = create_test_release_group([app], self.user)
		group.db_set("team", self.team.name)
		frappe.rename_doc("Team", self.team.name, self.user)
		frappe.set_user(self.user)
		deploy_candidate = create_test_deploy_candidate(group)
		deploy_candidate_build = create_test_deploy_candidate_build(deploy_candidate, no_build=True)
		try:
			deploy_candidate_build.insert()
		except frappe.PermissionError:
			self.fail("PermissionError raised in pre_build")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_deploy_with_empty_apps_creates_deploy_candidate_with_same_release(
		self, mock_enqueue_doc, mock_commit
	):
		"""
		Test if another deploy with empty apps_to_update creates Deploy Candidate with same release
		"""
		bench = create_test_bench()
		# Create another release
		source = frappe.get_doc("App Source", bench.apps[0].source)
		create_test_app_release(source)
		group = frappe.get_doc("Release Group", bench.group)
		first_candidate = frappe.get_doc("Deploy Candidate", bench.candidate)
		second_candidate = group.create_deploy_candidate([])
		self.assertEqual(first_candidate.apps[0].release, second_candidate.apps[0].release)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_deploy_with_no_arguments_creates_deploy_candidate_with_newer_release(
		self, mock_enqueue_doc, mock_commit
	):
		"""
		Test if another deploy with apps_to_update=None creates Deploy Candidate with newer release
		"""
		bench = create_test_bench()
		# Create another release
		source = frappe.get_doc("App Source", bench.apps[0].source)
		release = create_test_app_release(source)
		group = frappe.get_doc("Release Group", bench.group)
		first_candidate = frappe.get_doc("Deploy Candidate", bench.candidate)
		second_candidate = group.create_deploy_candidate()
		self.assertNotEqual(first_candidate.apps[0].release, second_candidate.apps[0].release)
		self.assertEqual(second_candidate.apps[0].release, release.name)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_deploy_with_specific_release_creates_deploy_candidate_with_that_release(
		self, mock_enqueue_doc, mock_commit
	):
		"""
		Test if another deploy with specific release creates Deploy Candidate with that release release
		"""
		bench = create_test_bench()
		# Create another release
		source = frappe.get_doc("App Source", bench.apps[0].source)
		second_release = create_test_app_release(source)
		third_release = create_test_app_release(source)
		group = frappe.get_doc("Release Group", bench.group)
		candidate = group.create_deploy_candidate([{"app": source.app, "release": second_release.name}])
		self.assertEqual(candidate.apps[0].release, second_release.name)
		self.assertNotEqual(candidate.apps[0].release, third_release.name)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_deploy_with_new_app_creates_deploy_candidate_with_new_app(self, mock_enqueue_doc, mock_commit):
		"""
		Test if another deploy with new app creates Deploy Candidate with new app
		"""
		bench = create_test_bench()
		# Create another app
		group = frappe.get_doc("Release Group", bench.group)
		app = create_test_app("erpnext", "ERPNext")
		source = create_test_app_source(group.version, app)
		release = create_test_app_release(source)
		group.update_source(source)
		candidate = group.create_deploy_candidate([{"app": app.name}])
		self.assertEqual(candidate.apps[1].app, app.name)
		self.assertEqual(candidate.apps[1].release, release.name)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc", new=foreground_enqueue_doc
	)
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.DeployCandidate.schedule_build_and_deploy",
		new=Mock(),
	)
	def test_creating_new_app_release_with_auto_deploy_deploys_that_app(self, mock_enqueue_doc):
		"""
		Test if creating a new app release with auto deploy creates a Deploy Candidate with most recent release of that app
		"""
		bench = create_test_bench()
		# Create another app
		group = frappe.get_doc("Release Group", bench.group)
		app = create_test_app("erpnext", "ERPNext")
		erpnext_source = create_test_app_source(group.version, app)
		group.update_source(erpnext_source)
		first_candidate = group.create_deploy_candidate(group.apps)

		dc_count_before = frappe.db.count("Deploy Candidate", filters={"group": group.name})

		# Enable auto deploy on ERPNext app
		group.apps[1].enable_auto_deploy = True
		group.save()

		# Create releases for both the apps
		frappe_source = frappe.get_doc("App Source", group.apps[0].source)
		create_test_app_release(frappe_source)
		create_test_app_release(erpnext_source)

		dc_count_after = frappe.db.count("Deploy Candidate", filters={"group": group.name})
		# We should have a new Deploy Candidate
		self.assertEqual(dc_count_after, dc_count_before + 1)

		second_candidate = frappe.get_last_doc("Deploy Candidate", {"group": group.name})
		# Only the app with auto deploy enabled should be updated
		self.assertEqual(second_candidate.apps[0].release, first_candidate.apps[0].release)
		self.assertNotEqual(second_candidate.apps[1].release, first_candidate.apps[1].release)

	@skip("Docker Build broken with `duplicate cache exports [gha]`")
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_app_cache_usage_on_subsequent_build(self):
		"""
		Tests if app cache is being used by a subsequent build,
		i.e. after cache has been set by a previous one.

		Creates two Deploy Candidates:
		1. apps: frappe, raven
		2. apps: frappe, wiki, raven

		When building the image of the second Deploy Candidate,
		raven should be fetched from app cache.
		"""
		from press.api.tests.test_bench import (
			set_press_settings_for_docker_build,
		)
		from press.press.doctype.bench_get_app_cache.bench_get_app_cache import (
			BenchGetAppCache,
		)

		team = create_test_team()
		apps = create_cache_test_apps(team)

		set_press_settings_for_docker_build()
		BenchGetAppCache.clear_app_cache()

		app_info_lists = [
			[apps["frappe"], apps["raven"]],
			[apps["frappe"], apps["wiki"], apps["raven"]],
		]

		dcs: list[DeployCandidate] = []
		for ail in app_info_lists:
			rg = create_cache_test_release_group(ail, team)
			dc = rg.create_deploy_candidate()
			dcs.append(dc)
			dc.build()

		"""
		Check if app cache was populated with apps included in
		the builds.
		"""
		cache_items = {v.app: v for v in BenchGetAppCache.get_data()}
		for name in ["raven", "wiki"]:
			file_name = cache_items.get(name, {}).get("file_name")
			self.assertTrue(file_name, f"app {name} not found in bench get-app cache")

			hash_stub = apps[name]["release"].hash[:10]
			self.assertTrue(hash_stub in file_name, "app found in cache does not match")

		"""
		Check if raven in the second Deploy Candidate was fetched
		from bench app cache.
		"""
		build_output = dcs[1].build_output
		if build_output:
			self.assertTrue("Getting raven from cache" in build_output)

	def test_chunked_packages(self, mock_enqueue_doc):
		"""
		Test if large list of packages is chunked correctly
		"""
		app = create_test_app()
		group = create_test_release_group([app])
		candidate = create_test_deploy_candidate(group)

		# Chromium dependencies
		packages = [
			"libasound2",
			"libatk-bridge2.0-0",
			"libatk1.0-0",
			"libatspi2.0-0",
			"libc6",
			"libcairo2",
			"libcups2",
			"libdbus-1-3",
			"libdrm2",
			"libexpat1",
			"libgbm1",
			"libglib2.0-0",
			"libnspr4",
			"libnss3",
			"libpango-1.0-0",
			"libpangocairo-1.0-0",
			"libstdc++6",
			"libudev1",
			"libuuid1",
			"libx11-6",
			"libx11-xcb1",
			"libxcb-dri3-0",
			"libxcb1",
			"libxcomposite1",
			"libxcursor1",
			"libxdamage1",
			"libxext6",
			"libxfixes3",
			"libxi6",
			"libxkbcommon0",
			"libxrandr2",
			"libxrender1",
			"libxshmfence1",
			"libxss1",
			"libxtst6",
		]
		candidate._add_packages(packages)

		# Assert that all chunks are below 140 characters
		chunks = [row.package for row in candidate.packages]
		self.assertTrue(all(len(chunk) < 140 for chunk in chunks))

		# # Assert that all packages are added
		chunked_pacakges = [package for chunk in chunks for package in chunk.split()]
		self.assertEqual(set(chunked_pacakges), set(packages))

	def test_build_fields_check(self, mock_enqueue_doc):
		app = create_test_app()
		intel_server = create_test_server(platform="x86_64").name
		arm_server = create_test_server(platform="arm64").name
		group = create_test_release_group([app], servers=[intel_server, arm_server])
		dc: DeployCandidate = group.create_deploy_candidate()

		self.assertEqual(dc.requires_arm_build, True)
		self.assertEqual(dc.requires_intel_build, True)

		group = create_test_release_group([app], servers=[intel_server])
		dc: DeployCandidate = group.create_deploy_candidate()

		self.assertEqual(dc.requires_intel_build, True)

		group = create_test_release_group([app], servers=[arm_server])
		dc: DeployCandidate = group.create_deploy_candidate()

		self.assertEqual(dc.requires_arm_build, True)


def create_cache_test_release_group(app_info_list: list["AppInfo"], team: "Team") -> "ReleaseGroup":
	title = f"Test App Cache RG {random.getrandbits(20):x}"
	doc_dict = {
		"doctype": "Release Group",
		"version": "Nightly",
		"enabled": True,
		"title": title,
		"team": team,
		"public": False,
		"use_app_cache": True,
		"compress_app_cache": True,
	}
	release_group: "ReleaseGroup" = frappe.get_doc(doc_dict)

	# Set apps
	for info in app_info_list:
		value = dict(app=info["app"].name, source=info["source"].name)
		release_group.append("apps", value)

	# Set BENCH_VERSION
	release_group.fetch_dependencies()
	for dep in release_group.dependencies:
		if dep.dependency != "BENCH_VERSION":
			continue
		dep.version = "5.22.6"

	release_group.insert(ignore_if_duplicate=True)
	release_group.reload()
	return release_group


def create_cache_test_apps(team: "Team") -> dict[str, "AppInfo"]:
	info = [
		(
			"https://github.com/frappe/frappe",
			"Frappe Framework",
			"Nightly",
			"develop",
			"d26c67df75a95ef43d329eadd48d7998ea656856",
		),
		(
			"https://github.com/frappe/wiki",
			"Frappe Wiki",
			"Nightly",
			"master",
			"8b369c63dd90b4f36195844d4a84e2aaa3b8f39a",
		),
		(
			"https://github.com/The-Commit-Company/raven",
			"Raven",
			"Nightly",
			"develop",
			"317de412bc4b66c21052a929021c1013bbe31335",
		),
	]

	apps = dict()
	for url, title, version, branch, hash in info:
		parts = url.split("/")
		name = parts[-1]
		app = create_test_app(name, title)
		source = app.add_source(
			frappe_version=version,
			repository_url=url,
			branch=branch,
			team=team.name,
			repository_owner=parts[-2],
		)

		release = create_test_app_release(source, hash)
		apps[name] = AppInfo(app=app, source=source, release=release)

	return apps
