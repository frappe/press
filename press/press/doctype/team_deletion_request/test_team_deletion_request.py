# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import unittest

import frappe
import requests
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.team_deletion_request.team_deletion_request import (
	TeamDeletionRequest,
)


class TestTeamDeletionRequest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.team = create_test_team()
		return super().setUpClass()

	@property
	def team_deletion_request(self):
		if not getattr(self, "_tdr", None):
			try:
				self._tdr = frappe.get_last_doc(
					"Team Deletion Request", filters={"team": self.team.name}
				)
			except frappe.DoesNotExistError:
				self._tdr = self.team.delete(workflow=True)
		return self._tdr

	def test_team_doc_deletion_raise(self):
		self.assertRaises(frappe.ValidationError, self.team.delete)

	def test_team_doc_deletion(self):
		self.assertIsInstance(self.team_deletion_request, TeamDeletionRequest)
		self.assertEqual(self.team_deletion_request.status, "Pending Verification")

	def test_url_for_verification(self):
		deletion_url = self.team_deletion_request.generate_url_for_confirmation()
		self.assertTrue(
			deletion_url.startswith(
				frappe.utils.get_url("/api/method/press.api.account.delete_team")
			)
		)

	def test_team_deletion_api(self):
		# TODO: Test if the API flow actually sets the status
		deletion_url = self.team_deletion_request.generate_url_for_confirmation()
		res = requests.get(deletion_url, allow_redirects=True)
		self.assertTrue(res.ok)
