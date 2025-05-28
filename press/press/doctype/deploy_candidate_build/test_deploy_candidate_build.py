# Copyright (c) 2025, Frappe and Contributors
# See license.txt


import typing
import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
	create_test_deploy_candidate_build,
	create_test_press_admin_team,
)
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestDeployCandidateBuild(unittest.TestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.user: str = self.team.user
		app = create_test_app()
		self.create_build_servers()
		group = create_test_release_group([app], self.user)
		group.db_set("team", self.team.name)
		frappe.set_user(self.user)
		self.deploy_candidate = create_test_deploy_candidate(group)
		self.deploy_candidate_build = create_test_deploy_candidate_build(self.deploy_candidate)

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def create_build_servers(self):
		self.x86_build_server = create_test_server(platform="x86_64", use_for_build=True)
		self.arm_build_server = create_test_server(platform="arm64", use_for_build=True)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc", new=Mock())
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock())
	@patch.object(DeployCandidateBuild, "_build", new=Mock())
	def test_creation_of_arm_build(self, mock_enqueue_doc):
		self.deploy_candidate_build.insert()
		with self.assertRaises(frappe.ValidationError):
			# Since x86 build is in intermediate state.
			self.deploy_candidate_build.create_arm_build()

		self.deploy_candidate_build.status = "Failure"
		self.deploy_candidate_build.save()

		with self.assertRaises(frappe.ValidationError):
			# Since x86 build is in failed state.
			self.deploy_candidate_build.create_arm_build()

		self.deploy_candidate_build.status = "Success"
		self.deploy_candidate_build.save()

		arm_build = self.deploy_candidate_build.create_arm_build()
		self.assertEqual(
			"x86_64", frappe.get_value("Deploy Candidate Build", self.deploy_candidate_build.name, "platform")
		)
		self.assertEqual("arm64", frappe.get_value("Deploy Candidate Build", arm_build, "platform"))

		with self.assertRaises(frappe.ValidationError):
			# Since arm build already exists
			self.deploy_candidate_build.create_arm_build()

		for dep in self.deploy_candidate.dependencies:
			if dep.dependency == "WKHTMLTOPDF_VERSION":
				dep.version = "0.12.4"

		self.deploy_candidate.save()

		with self.assertRaises(frappe.ValidationError):
			# Since wkhtmltopdf version is not supported!
			self.deploy_candidate_build.create_arm_build()

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc", new=Mock())
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock())
	@patch.object(DeployCandidateBuild, "_process_run_build", new=Mock())
	def test_correct_build_flow(self, mock_enqueue):
		import json

		app = create_test_app()

		group = create_test_release_group([app], servers=[self.x86_build_server, self.arm_build_server])

		dc: DeployCandidate = group.create_deploy_candidate()
		deploy_candidate_build_name = dc.build().get("message")

		deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build", deploy_candidate_build_name
		)

		deploy_candidate_build.set_build_server()
		build_server_platform = frappe.get_value("Server", deploy_candidate_build.build_server, "platform")
		self.assertEqual(build_server_platform, "x86_64")
		deploy_candidate_build.status = "Success"
		deploy_candidate_build.save()

		job = frappe._dict(
			{"request_data": json.dumps({"deploy_candidate_build": deploy_candidate_build_name})}
		)
		deploy_candidate_build.process_run_build(job, response_data=None)

		# Intel build has finished and been processed
		dc: DeployCandidate = dc.reload()
		self.assertEqual(dc.intel_build, deploy_candidate_build_name)

		# Auto triggered from process run build of the last dc
		newly_created_build: DeployCandidateBuild = frappe.get_last_doc(
			"Deploy Candidate Build", {"deploy_candidate": dc.name}
		)
		self.assertEqual(newly_created_build.platform, "arm64")

		job = frappe._dict({"request_data": json.dumps({"deploy_candidate_build": newly_created_build.name})})
		newly_created_build.status = "Success"
		newly_created_build.save()
		newly_created_build.process_run_build(job, response_data=None)

		# ARM Build has finished and been processed
		dc: DeployCandidate = dc.reload()
		self.assertEqual(dc.arm_build, newly_created_build.name)

		# Assert no more builds are created
		test_build: DeployCandidateBuild = frappe.get_last_doc(
			"Deploy Candidate Build", {"deploy_candidate": dc.name}
		)
		self.assertEqual(test_build.name, newly_created_build.name)
