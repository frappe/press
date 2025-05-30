# Copyright (c) 2025, Frappe and Contributors
# See license.txt
import typing
import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord


class TestARMBuildRecord(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		virtual_machine = create_test_virtual_machine(series="f")
		virtual_machine.create_server()
		cls.server = frappe.get_last_doc("Server")
		app = create_test_app()
		rg = create_test_release_group([app], servers=[cls.server])
		cls.bench = create_test_bench(group=rg, server=cls.server)
		cls.build = frappe.get_value("Deploy Candidate Build", {})
		frappe.db.set_value("Deploy Candidate Build", {"name": cls.build}, field="status", val="Success")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

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
