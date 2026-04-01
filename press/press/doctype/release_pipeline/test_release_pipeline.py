# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_and_update
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.utils import get_current_team
from press.utils.test import foreground_enqueue_doc

if typing.TYPE_CHECKING:
	from press.press.doctype.release_pipeline.release_pipeline import ReleasePipeline


class TestReleasePipeline(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		server = create_test_server(use_for_build=True)
		cls.test_frappe_app = create_test_app("frappe")
		cls.test_erpnext_app = create_test_app("erpnext", "Erpnext App")
		cls.test_frappe_release = create_test_app_release(
			create_test_app_source(app=cls.test_frappe_app, version="Version 15"), "random-hash"
		)
		cls.test_erpnext_release = create_test_app_release(
			create_test_app_source(app=cls.test_erpnext_app, version="Version 15"), "random-hash"
		)
		cls.test_release_group = create_test_release_group(
			apps=[cls.test_frappe_app, cls.test_erpnext_app],
			frappe_version="Version 15",
			servers=[server.name],
		)

	@patch(
		"press.workflow_engine.doctype.press_workflow_task.press_workflow_task.frappe.enqueue_doc",
		foreground_enqueue_doc,
	)
	@patch.object(MariaDBDatabase, "commit", Mock())
	def test_release_pipeline_creation(self):
		deploy_and_update(
			self.test_release_group.name,
			apps=[
				{
					"app": "frappe",
					"source": "SRC-Frappe-001",
					"release": self.test_frappe_release.name,
					"hash": "random-hash",
				},
				{
					"app": "erpnext",
					"source": "SRC-Erpnext-001",
					"release": self.test_erpnext_release.name,
					"hash": "random-hash-2",
				},
			],
			run_will_fail_check=False,
		)

		release_pipeline: ReleasePipeline = frappe.get_last_doc("Release Pipeline")
		self.assertEqual(release_pipeline.release_group, self.test_release_group.name)
		self.assertEqual(release_pipeline.team, get_current_team())
		self.assertEqual(release_pipeline.status, "Running")
		release_pipeline = frappe.get_doc(
			"Press Workflow",
			{
				"linked_doctype": "Release Pipeline",
				"linked_docname": release_pipeline.name,
			},
		)

		frappe.get_last_doc("Press Workflow")
