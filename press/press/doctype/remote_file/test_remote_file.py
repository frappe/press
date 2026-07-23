# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from datetime import datetime


def create_test_remote_file(
	site: str | None = None,
	creation: datetime | None = None,
	file_path: str | None = None,
	file_size: int = 1024,
	bucket: str | None = None,
):
	"""Create test remote file doc for required timestamp."""
	creation = creation or frappe.utils.now_datetime()
	remote_file = frappe.get_doc(
		{
			"doctype": "Remote File",
			"status": "Available",
			"site": site,
			"file_path": file_path,
			"file_size": file_size,
			"bucket": bucket,
		}
	).insert(ignore_if_duplicate=True)
	remote_file.db_set("creation", creation)
	remote_file.reload()
	return remote_file


class TestRemoteFile(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_remote_file_of_site_belongs_to_sites_team_and_not_session_users_team(self):
		"""Backup remote files are created in agent job callbacks, as Administrator."""
		from press.press.doctype.site.test_site import create_test_site
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		site = create_test_site(team=team.name)

		remote_file = create_test_remote_file(site=site.name)

		self.assertEqual(remote_file.team, team.name)

	def test_patch_resets_team_of_remote_files_stamped_with_the_wrong_team(self):
		from press.patches.v0_8_0.fix_remote_file_team_from_site import fix_teams
		from press.press.doctype.site.test_site import create_test_site
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		site = create_test_site(team=team.name)
		remote_file = create_test_remote_file(site=site.name)
		remote_file.db_set("team", create_test_team().name)

		with patch.object(frappe.db, "commit"):  # keep the test rollback-able
			fix_teams()

		self.assertEqual(frappe.db.get_value("Remote File", remote_file.name, "team"), team.name)
