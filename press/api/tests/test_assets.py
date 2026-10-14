from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import botocore.exceptions
import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.assets import get_asset_urls, upload_asset
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
	create_test_deploy_candidate_build,
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


class TestGetAssetUrls(FrappeTestCase):
	def setUp(self):
		super().setUp()
		team = create_test_press_admin_team()
		apps = [create_test_app(), create_test_app("erpnext", "ERPNext")]
		self.group = create_test_release_group(apps, team.user)
		self.group.db_set("public", 1)
		self.candidate = create_test_deploy_candidate(self.group)
		self.candidate.db_set("build_token", "test-build-token")
		# run_build=0 skips after_insert starting a real build, which needs a build server
		build = create_test_deploy_candidate_build(self.candidate, status="Running")
		build.run_build = 0
		self.build = build.insert()
		self.erpnext_hash = next(app.hash for app in self.candidate.apps if app.app == "erpnext")

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def get_asset_urls(self, stored: bool = False, token: str = "test-build-token", hash: str | None = None):
		request = SimpleNamespace(headers={"build-token": token})
		with (
			patch.object(frappe, "request", request),
			patch("press.api.assets._get_asset_store", return_value=(mock_asset_store(stored), "bucket")),
		):
			return get_asset_urls("erpnext", hash or self.erpnext_hash)

	def test_build_gets_a_download_url_when_the_assets_are_stored(self):
		self.assertEqual(self.get_asset_urls(stored=True), {"download_url": "https://signed/get_object"})

	def test_build_gets_an_upload_url_when_the_assets_are_not_stored(self):
		self.assertEqual(self.get_asset_urls(stored=False), {"upload_url": "https://signed/put_object"})

	def test_unknown_build_token_is_refused(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Invalid build token used"):
			self.get_asset_urls(token="not-a-token")

	def test_token_of_a_build_that_is_no_longer_running_is_refused(self):
		self.build.db_set("status", "Success")
		with self.assertRaisesRegex(frappe.PermissionError, "Expired token used"):
			self.get_asset_urls()

	def test_private_group_build_is_refused(self):
		self.group.db_set("public", 0)
		with self.assertRaisesRegex(frappe.PermissionError, "only available to public bench groups"):
			self.get_asset_urls()

	def test_commit_that_is_not_part_of_the_build_is_refused(self):
		with self.assertRaisesRegex(frappe.PermissionError, "is not part of this build"):
			self.get_asset_urls(hash="0" * 40)


class TestUploadAsset(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_user_without_system_manager_cannot_upload_to_the_asset_store(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			upload_asset()
