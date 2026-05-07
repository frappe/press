# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.team.test_team import create_test_team


class TestYankedAppRelease(FrappeTestCase):
	"""YankedAppRelease.after_insert marks the linked App Release as Yanked so it
	can no longer be used in new Deploy Candidates. on_trash restores the release
	to Approved when the yank record is deleted.

	If after_insert is broken, yanked releases remain deployable and malicious
	or broken code can reach customer sites. If on_trash is broken, a corrected
	release stays permanently locked out of deploys.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		self.release = create_test_app_release(self.source)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _yank(self):
		return frappe.get_doc(
			{
				"doctype": "Yanked App Release",
				"parent_app_release": self.release.name,
				"hash": self.release.hash,
				"team": self.team.name,
			}
		).insert(ignore_permissions=True)

	def test_after_insert_marks_release_as_yanked(self):
		self._yank()
		self.release.reload()
		self.assertEqual(self.release.status, "Yanked")
		self.assertTrue(self.release.invalid_release)
		self.assertEqual(self.release.invalidation_reason, "Yanked-Release")

	def test_on_trash_restores_release_to_approved(self):
		yank = self._yank()
		self.release.reload()
		self.assertEqual(self.release.status, "Yanked")

		yank.delete(ignore_permissions=True)
		self.release.reload()

		self.assertEqual(self.release.status, "Approved")
		self.assertFalse(self.release.invalid_release)
		self.assertEqual(self.release.invalidation_reason, "")
