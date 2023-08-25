# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
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
