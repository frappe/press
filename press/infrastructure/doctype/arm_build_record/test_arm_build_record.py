# Copyright (c) 2025, Frappe and Contributors
# See license.txt
import typing
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord


@patch("press.press.doctype.bench.bench.frappe.db.commit", new=MagicMock)
@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
@patch("press.api.bench.frappe.db.commit", new=MagicMock)
class TestARMBuildRecord(FrappeTestCase):
	def setUp(self):
		super().setUp()

		virtual_machine = create_test_virtual_machine(series="f")
		virtual_machine.create_server()
		self.server = frappe.get_last_doc("Server")
		app = create_test_app()
		rg = create_test_release_group([app], servers=[self.server.name])
		self.bench = create_test_bench(group=rg, server=self.server.name)
		self.build = frappe.get_value("Deploy Candidate Build", {})
		frappe.db.set_value("Deploy Candidate Build", {"name": self.build}, field="status", val="Success")

	@patch.object(DeployCandidateBuild, "pre_build", new=Mock())
	def test_build_trigger(self):
		self.server.collect_arm_images()
		arm_build_record: ARMBuildRecord = frappe.get_doc(
			"ARM Build Record", frappe.get_value("ARM Build Record", {})
		)
		deploy_candidate = frappe.get_value("Deploy Candidate Build", self.build, "deploy_candidate")
		for image in arm_build_record.arm_images:
			# Assert that the arm build is attached and created for the intel build
			self.assertEqual(
				image.build, frappe.db.get_value("Deploy Candidate", deploy_candidate, "arm_build")
			)

		# Assert no bench update on app server without image pull.
		with self.assertRaises(frappe.ValidationError):
			arm_build_record.update_image_tags_on_benches()
