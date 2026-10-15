from unittest.mock import MagicMock, patch

import botocore.exceptions
import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.assets import get_asset_store_instructions, upload_asset
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
	create_test_press_admin_team,
)
from press.press.doctype.release_group.test_release_group import create_test_release_group


def mock_asset_store(stored: bool) -> MagicMock:
	client = MagicMock()
	if not stored:
		client.head_object.side_effect = botocore.exceptions.ClientError(
			{"Error": {"Code": "404"}}, "HeadObject"
		)
	client.generate_presigned_url.side_effect = lambda method, Params, ExpiresIn: f"https://signed/{method}"
	return client


class TestAssetStoreInstructions(FrappeTestCase):
	def setUp(self):
		super().setUp()
		team = create_test_press_admin_team()
		apps = [create_test_app(), create_test_app("erpnext", "ERPNext")]
		self.candidate = create_test_deploy_candidate(create_test_release_group(apps, team.user))
		for app in self.candidate.apps:
			app.use_cached = 1
		self.erpnext = next(app for app in self.candidate.apps if app.app == "erpnext")

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def get_instructions(self, stored: bool, can_upload: bool = True) -> list[dict[str, str]]:
		with patch("press.api.assets._get_asset_store", return_value=(mock_asset_store(stored), "bucket")):
			return get_asset_store_instructions(self.candidate.apps, can_upload)

	def test_stored_assets_get_a_download_url(self):
		self.assertEqual(
			self.get_instructions(stored=True),
			[{"app": "erpnext", "hash": self.erpnext.hash, "download_url": "https://signed/get_object"}],
		)

	def test_assets_not_stored_get_an_upload_url(self):
		self.assertEqual(
			self.get_instructions(stored=False),
			[{"app": "erpnext", "hash": self.erpnext.hash, "upload_url": "https://signed/put_object"}],
		)

	def test_build_that_cannot_upload_only_downloads(self):
		self.assertEqual(self.get_instructions(stored=False, can_upload=False), [])
		self.assertEqual(
			self.get_instructions(stored=True, can_upload=False)[0]["download_url"],
			"https://signed/get_object",
		)

	def test_apps_without_app_cache_are_left_out(self):
		self.erpnext.use_cached = 0
		self.assertEqual(self.get_instructions(stored=True), [])

	def test_unreachable_store_leaves_the_build_to_build_assets_itself(self):
		with (
			patch("press.api.assets._get_asset_store", side_effect=Exception("store unreachable")),
			patch("press.api.assets.frappe.log_error"),
		):
			self.assertEqual(get_asset_store_instructions(self.candidate.apps, can_upload=True), [])


class TestUploadAsset(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_user_without_system_manager_cannot_upload_to_the_asset_store(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			upload_asset()
