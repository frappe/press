# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.app_release import is_update_after_deployed
from press.press.doctype.release_group.release_group import can_use_release
from press.press.doctype.team.test_team import create_test_team

if typing.TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource


def create_test_app_release(app_source: AppSource, hash: str | None = None) -> "AppRelease":
	"""Create test app release given App source."""
	hash = hash or frappe.mock("sha1")
	app_release = frappe.get_doc(
		{
			"doctype": "App Release",
			"app": app_source.app,
			"source": app_source.name,
			"hash": hash,
			"message": "Test Msg",
			"author": "Test Author",
			"team": app_source.team,
			"deployable": True,
			"status": "Approved",
		}
	).insert(ignore_if_duplicate=True, ignore_links=True)
	app_release.reload()
	return app_release


class TestCanUseRelease(FrappeTestCase):
	"""can_use_release gates which App Releases are eligible for deploy candidate selection.

	For private app sources (public=False), any release status is allowed — the
	team owns the code and can deploy whatever they like.

	For public app sources (marketplace/public repos), only Approved and Draft
	releases are allowed.  Yanked, Rejected, and Awaiting Approval must be blocked
	to prevent:
	- Yanked: a release pulled back due to security/critical bug from reaching new benches
	- Rejected: a marketplace review rejection meaning the release must not go live
	- Awaiting Approval: unreviewed marketplace code must not bypass review
	"""

	def _release(self, public: bool, status: str) -> frappe._dict:
		return frappe._dict(public=public, status=status)

	# --- private sources: all statuses allowed ---

	def test_private_approved_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=False, status="Approved")))

	def test_private_draft_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=False, status="Draft")))

	def test_private_yanked_release_is_usable(self):
		# Owner controls their own code — yanked on marketplace doesn't restrict private deploy
		self.assertTrue(can_use_release(self._release(public=False, status="Yanked")))

	def test_private_rejected_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=False, status="Rejected")))

	def test_private_awaiting_approval_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=False, status="Awaiting Approval")))

	# --- public sources: only Approved and Draft allowed ---

	def test_public_approved_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=True, status="Approved")))

	def test_public_draft_release_is_usable(self):
		self.assertTrue(can_use_release(self._release(public=True, status="Draft")))

	def test_public_yanked_release_is_not_usable(self):
		self.assertFalse(can_use_release(self._release(public=True, status="Yanked")))

	def test_public_rejected_release_is_not_usable(self):
		self.assertFalse(can_use_release(self._release(public=True, status="Rejected")))

	def test_public_awaiting_approval_release_is_not_usable(self):
		self.assertFalse(can_use_release(self._release(public=True, status="Awaiting Approval")))


class TestIsUpdateAfterDeployed(FrappeTestCase):
	"""is_update_after_deployed decides ordering when calculating release diffs.

	If the comparison is inverted, diffs would be generated in the wrong direction
	(new→old instead of old→new), making the diff useless and potentially causing
	incorrect pull_update decisions for delta builds.

	Falls back to creation time when commit timestamps are absent (common for
	releases created via API without a timestamp).
	"""

	_base = datetime(2024, 1, 1, 12, 0, 0)

	def _r(self, timestamp=None, creation=None):
		return frappe._dict(
			timestamp=timestamp,
			creation=creation or self._base,
		)

	def test_newer_timestamp_is_update(self):
		deployed = self._r(timestamp=self._base)
		update = self._r(timestamp=self._base + timedelta(hours=1))
		self.assertTrue(is_update_after_deployed(update, deployed))

	def test_older_timestamp_is_not_update(self):
		deployed = self._r(timestamp=self._base)
		update = self._r(timestamp=self._base - timedelta(hours=1))
		self.assertFalse(is_update_after_deployed(update, deployed))

	def test_falls_back_to_creation_when_timestamps_absent(self):
		deployed = self._r(timestamp=None, creation=self._base)
		update = self._r(timestamp=None, creation=self._base + timedelta(days=1))
		self.assertTrue(is_update_after_deployed(update, deployed))

	def test_creation_fallback_returns_false_for_older_release(self):
		deployed = self._r(timestamp=None, creation=self._base)
		update = self._r(timestamp=None, creation=self._base - timedelta(days=1))
		self.assertFalse(is_update_after_deployed(update, deployed))

	def test_mixed_timestamps_falls_back_to_creation(self):
		# Only one side has a timestamp — condition `if update_ts and deployed_ts` fails
		deployed = self._r(timestamp=None, creation=self._base)
		update = self._r(timestamp=self._base + timedelta(hours=1), creation=self._base + timedelta(days=1))
		self.assertTrue(is_update_after_deployed(update, deployed))


class TestAppReleaseAutoApproval(FrappeTestCase):
	"""AppRelease.before_save auto-approves releases for trusted teams and featured apps.

	If this logic breaks, featured app developers wait for manual approval on every commit
	and auto-release teams lose trusted-publisher status, stacking releases as
	"Awaiting Approval" and blocking deploys.

	Conversely, if the condition is accidentally widened (e.g. `or True`), any team
	could push unapproved marketplace code to customer sites.
	"""

	def setUp(self):
		super().setUp()
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _make_release(self, status="Awaiting Approval") -> "AppRelease":
		return frappe.get_doc(
			{
				"doctype": "App Release",
				"app": self.app.name,
				"source": self.source.name,
				"hash": frappe.mock("sha1"),
				"message": "Test commit",
				"author": "tester",
				"team": self.team.name,
				"status": status,
			}
		)

	def test_featured_app_release_is_auto_approved(self):
		# Featured App child links to Marketplace App (which uses app name as its name)
		frappe.get_doc(
			{
				"doctype": "Marketplace App",
				"app": self.app.name,
				"description": "test",
				"team": self.team.name,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		ms = frappe.get_single("Marketplace Settings")
		ms.append("featured_apps", {"app": self.app.name})
		ms.save(ignore_permissions=True)

		release = self._make_release(status="Awaiting Approval")
		release.insert(ignore_permissions=True)

		self.assertEqual(release.status, "Approved")

	def test_auto_release_team_release_is_auto_approved(self):
		ms = frappe.get_single("Marketplace Settings")
		ms.append("auto_release_teams", {"team": self.team.name})
		ms.save(ignore_permissions=True)

		release = self._make_release(status="Awaiting Approval")
		release.insert(ignore_permissions=True)

		self.assertEqual(release.status, "Approved")

	def test_regular_team_release_is_not_auto_approved(self):
		# team is NOT in auto_release_teams; app is NOT featured
		release = self._make_release(status="Awaiting Approval")
		release.insert(ignore_permissions=True)

		self.assertEqual(release.status, "Awaiting Approval")


class TestGetUnpublishedMarketplaceReleases(FrappeTestCase):
	"""get_unpublished_marketplace_releases is the last line of defence before a
	Deploy Candidate can trigger a build for marketplace apps.

	If this returns an empty list when it should return unapproved releases, the
	deploy proceeds with code that has not passed marketplace review — potentially
	shipping malicious or broken code to all customer sites using that app.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _register_marketplace_source(self):
		"""Register the source as a Marketplace App Version so the DC recognises it."""
		return frappe.get_doc(
			{
				"doctype": "Marketplace App",
				"app": self.app.name,
				"description": "Test",
				"team": self.team.name,
				"sources": [{"version": "Version 14", "source": self.source.name}],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	def _make_dc_with_release(self, release_status: str):
		from press.press.doctype.deploy_candidate.test_deploy_candidate import create_test_deploy_candidate
		from press.press.doctype.release_group.test_release_group import create_test_release_group

		release = frappe.get_doc(
			{
				"doctype": "App Release",
				"app": self.app.name,
				"source": self.source.name,
				"hash": frappe.mock("sha1"),
				"message": "commit",
				"author": "tester",
				"team": self.team.name,
				"status": release_status,
			}
		).insert(ignore_permissions=True)

		rg = create_test_release_group([self.app], app_sources=[self.source.name])
		dc = create_test_deploy_candidate(rg)

		# Overwrite the auto-selected release with our test release
		for app_row in dc.apps:
			if app_row.app == self.app.name:
				app_row.release = release.name
		dc.save()

		return dc, release

	def test_no_marketplace_sources_returns_empty(self):
		from press.press.doctype.deploy_candidate.test_deploy_candidate import create_test_deploy_candidate
		from press.press.doctype.release_group.test_release_group import create_test_release_group

		# Source is NOT registered as a Marketplace App Version
		rg = create_test_release_group([self.app], app_sources=[self.source.name])
		dc = create_test_deploy_candidate(rg)

		self.assertEqual(dc.get_unpublished_marketplace_releases(), [])

	def test_approved_marketplace_release_returns_empty(self):
		self._register_marketplace_source()
		dc, _ = self._make_dc_with_release("Approved")
		self.assertEqual(dc.get_unpublished_marketplace_releases(), [])

	def test_rejected_marketplace_release_is_flagged(self):
		self._register_marketplace_source()
		dc, release = self._make_dc_with_release("Rejected")
		unpublished = dc.get_unpublished_marketplace_releases()
		self.assertIn(release.name, unpublished)

	def test_yanked_marketplace_release_is_flagged(self):
		self._register_marketplace_source()
		dc, release = self._make_dc_with_release("Yanked")
		unpublished = dc.get_unpublished_marketplace_releases()
		self.assertIn(release.name, unpublished)

	def test_awaiting_approval_marketplace_release_is_flagged(self):
		self._register_marketplace_source()
		dc, release = self._make_dc_with_release("Awaiting Approval")
		unpublished = dc.get_unpublished_marketplace_releases()
		self.assertIn(release.name, unpublished)


class TestAutoDeployMarker(FrappeTestCase):
	"""_has_auto_deploy_marker parses a deploy marker from the commit message.

	Embedding "[deploy]" (or the configured marker) in a commit message deploys to
	groups tagged auto-deploy, or to a specific bench group via "-<group>" suffix.

	If the parsing is wrong: "[deploy]-my-bench" deploys to the wrong bench group,
	or a marker absent from the message triggers an unexpected deploy on every commit.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		# Store original to restore in tearDown
		self._original_marker = frappe.db.get_single_value("Press Settings", "deploy_marker")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Press Settings", "deploy_marker", self._original_marker or "")
		frappe.db.rollback()

	def _release(self, message: str):
		"""Build an unsaved AppRelease with the given commit message."""
		return frappe.get_doc(
			doctype="App Release",
			app=self.app.name,
			source=self.source.name,
			hash=frappe.mock("sha1"),
			message=message,
			author="tester",
			team=self.team.name,
			status="Approved",
		)

	def test_no_marker_configured_never_deploys(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "")
		release = self._release("feat: add thing [deploy]")
		has_deploy, bench_group = release._has_auto_deploy_marker()
		self.assertFalse(has_deploy)
		self.assertIsNone(bench_group)

	def test_marker_absent_from_message_returns_false(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "[deploy]")
		release = self._release("chore: update changelog")
		has_deploy, _ = release._has_auto_deploy_marker()
		self.assertFalse(has_deploy)

	def test_empty_message_returns_false(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "[deploy]")
		release = self._release("")
		has_deploy, _ = release._has_auto_deploy_marker()
		self.assertFalse(has_deploy)

	def test_marker_in_message_returns_true_with_no_group(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "[deploy]")
		release = self._release("fix: critical patch [deploy]")
		has_deploy, bench_group = release._has_auto_deploy_marker()
		self.assertTrue(has_deploy)
		self.assertIsNone(bench_group)

	def test_marker_with_bench_group_suffix_is_parsed(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "[deploy]")
		# "[deploy]-my-bench" → bench_group = "my-bench"
		release = self._release("fix: patch [deploy]-my-bench")
		has_deploy, bench_group = release._has_auto_deploy_marker()
		self.assertTrue(has_deploy)
		self.assertEqual(bench_group, "my-bench")

	def test_marker_with_no_suffix_after_dash_gives_none_group(self):
		frappe.db.set_single_value("Press Settings", "deploy_marker", "[deploy]")
		# "[deploy]" with nothing after it → bench_group should be None (or empty)
		release = self._release("fix: patch [deploy]")
		_, bench_group = release._has_auto_deploy_marker()
		# Empty string after split means bench_group resolves to None
		self.assertFalse(bench_group)  # None or ""


class TestAutoDeployCheckbox(FrappeTestCase):
	"""The 'Enable Auto Deploy' checkbox on each Release Group App controls whether
	a new commit to that app's source triggers an automatic deploy.

	Checkbox OFF means the app must never be auto-deployed (teams pin versions for
	stability). Checkbox ON must not start a build while one is already running, as
	overlapping builds cause race conditions and leave sites with inconsistent versions.
	"""

	def setUp(self):
		super().setUp()
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()

		self.app1 = create_test_app("frappe", "Frappe Framework")
		self.app2 = create_test_app("erpnext", "ERPNext")
		self.source1 = create_test_app_source("Version 14", self.app1, team=self.team.name)
		self.source2 = create_test_app_source("Version 14", self.app2, team=self.team.name)
		# Create an approved release for app1 so the RG has something to pin
		create_test_app_release(self.source1)

		from press.press.doctype.release_group.test_release_group import create_test_release_group

		self.rg = create_test_release_group(
			[self.app1, self.app2],
			app_sources=[self.source1.name, self.source2.name],
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _new_release(self, source):
		return frappe.get_doc(
			doctype="App Release",
			app=source.app,
			source=source.name,
			hash=frappe.mock("sha1"),
			message="New commit",
			author="tester",
			team=self.team.name,
			status="Approved",
		).insert(ignore_permissions=True)

	@patch("press.press.doctype.app_release.app_release.AppRelease.trigger_deploy_via_commit_markers")
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.DeployCandidate.schedule_build_and_deploy",
		new=Mock(),
	)
	def test_app_without_checkbox_does_not_trigger_deploy(self, _mock_marker_deploy):
		# app2 has enable_auto_deploy=False (default) on the RG
		for app_row in self.rg.apps:
			app_row.enable_auto_deploy = False
		self.rg.save()

		dc_count_before = frappe.db.count("Deploy Candidate", {"group": self.rg.name})
		release = self._new_release(self.source2)
		release.auto_deploy()
		dc_count_after = frappe.db.count("Deploy Candidate", {"group": self.rg.name})

		self.assertEqual(dc_count_before, dc_count_after)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.DeployCandidate.schedule_build_and_deploy",
		new=Mock(),
	)
	def test_app_with_checkbox_triggers_deploy(self):
		# Only app2 has auto-deploy enabled
		for app_row in self.rg.apps:
			app_row.enable_auto_deploy = app_row.app == self.app2.name
		self.rg.save()

		dc_count_before = frappe.db.count("Deploy Candidate", {"group": self.rg.name})
		release = self._new_release(self.source2)
		release.auto_deploy()
		dc_count_after = frappe.db.count("Deploy Candidate", {"group": self.rg.name})

		self.assertEqual(dc_count_after, dc_count_before + 1)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.DeployCandidate.schedule_build_and_deploy",
		new=Mock(),
	)
	def test_running_build_prevents_concurrent_auto_deploy(self):
		# Enable auto-deploy for app2
		for app_row in self.rg.apps:
			app_row.enable_auto_deploy = app_row.app == self.app2.name
		self.rg.save()

		# Simulate an in-progress build for this group
		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild

		with patch.object(DeployCandidateBuild, "after_insert"):
			frappe.get_doc(
				doctype="Deploy Candidate Build",
				deploy_candidate="stub-dc",
				group=self.rg.name,
				team=self.team.name,
				status="Running",
			).insert(ignore_permissions=True, ignore_links=True)

		dc_count_before = frappe.db.count("Deploy Candidate", {"group": self.rg.name})
		release = self._new_release(self.source2)
		release.auto_deploy()
		dc_count_after = frappe.db.count("Deploy Candidate", {"group": self.rg.name})

		# No new DC should be created while a build is already running
		self.assertEqual(dc_count_before, dc_count_after)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.DeployCandidate.schedule_build_and_deploy",
		new=Mock(),
	)
	def test_only_auto_deploy_apps_included_in_candidate(self):
		"""DC created by auto_deploy must contain ONLY the auto-deploy-enabled app."""
		# app1: auto-deploy OFF, app2: auto-deploy ON
		for app_row in self.rg.apps:
			app_row.enable_auto_deploy = app_row.app == self.app2.name
		self.rg.save()

		release = self._new_release(self.source2)
		release.auto_deploy()

		dc = frappe.get_last_doc("Deploy Candidate", {"group": self.rg.name})
		dc_app_names = [row.app for row in dc.apps]

		# app2 must be present
		self.assertIn(self.app2.name, dc_app_names)
		# app1 must also be present (it gets pinned at its current release)
		# but its release must NOT have been updated to a newer one
		app1_row_in_dc = next(r for r in dc.apps if r.app == self.app1.name)
		# The pinned release for app1 should be the one from the last deployed bench,
		# not any hypothetical newer release — so it must NOT equal app2's new release
		self.assertNotEqual(app1_row_in_dc.release, release.name)
