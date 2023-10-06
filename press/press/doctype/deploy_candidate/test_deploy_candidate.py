# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
from press.press.doctype.release_group.release_group import ReleaseGroup

import unittest

import frappe

from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)


def create_test_deploy_candidate(group: ReleaseGroup) -> DeployCandidate:
	"""
	Create Test Deploy Candidate doc
	"""
	deploy_candidate = frappe.get_doc(
		{
			"doctype": "Deploy Candidate",
			"team": group.team,
			"group": group.name,
			"apps": group.apps,
			"dependencies": group.dependencies,
		}
	)
	deploy_candidate.insert()
	return deploy_candidate


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestDeployCandidate(unittest.TestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.user: str = self.team.user

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
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
		try:
			deploy_candidate.pre_build(method="_build")
		except frappe.PermissionError:
			self.fail("PermissionError raised in pre_build")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
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
		try:
			deploy_candidate.pre_build(method="_build")
		except frappe.PermissionError:
			self.fail("PermissionError raised in pre_build")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_first_deploy_creates_draft_deploy_candidate(
		self, mock_enqueue_doc, mock_commit
	):
		"""
		Test if first deploy creates Deploy Candidate doc
		"""
		app = create_test_app()
		source = create_test_app_source("Nightly", app)
		create_test_app_release(source)
		group = create_test_release_group([app])
		candidate = group.create_deploy_candidate()
		self.assertEqual(candidate.status, "Draft")

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
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

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
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

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
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
		candidate = group.create_deploy_candidate(
			[{"app": source.app, "release": second_release.name}]
		)
		self.assertEqual(candidate.apps[0].release, second_release.name)
		self.assertNotEqual(candidate.apps[0].release, third_release.name)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc")
	def test_deploy_with_new_app_creates_deploy_candidate_with_new_app(
		self, mock_enqueue_doc, mock_commit
	):
		"""
		Test if another deploy with new app creates Deploy Candidate with new app
		"""
		bench = create_test_bench()
		# Create another app
		group = frappe.get_doc("Release Group", bench.group)
		app = create_test_app("erpnext", "ERPNext")
		source = create_test_app_source(group.version, app)
		release = create_test_app_release(source)
		group.add_app(source)
		candidate = group.create_deploy_candidate([{"app": app.name}])
		self.assertEqual(candidate.apps[1].app, app.name)
		self.assertEqual(candidate.apps[1].release, release.name)
