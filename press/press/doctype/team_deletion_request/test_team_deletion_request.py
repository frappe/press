# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.team_deletion_request.team_deletion_request import (
	TeamDeletionRequest,
	request_team_deletion,
)
from press.utils.test import request_locally_with_host_rewrite


class TestTeamDeletionRequest(FrappeTestCase):
	def setUp(self) -> None:
		super().setUp()
		self.team = create_test_team()
		sendmail = patch.object(frappe, "sendmail")
		self.sendmail = sendmail.start()
		self.addCleanup(sendmail.stop)

	def tearDown(self) -> None:
		super().tearDown()
		frappe.db.delete("Team", {"name": self.team.name})
		frappe.db.truncate("Team Deletion Request")

	@property
	def team_deletion_request(self) -> TeamDeletionRequest:
		if not getattr(self, "_tdr", None):
			try:
				self._tdr = frappe.get_last_doc("Team Deletion Request", filters={"team": self.team.name})
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
			deletion_url.startswith(frappe.utils.get_url("/api/method/press.api.account.delete_team"))
		)

	def test_team_deletion_api(self):
		# TODO: Test if the API flow actually sets the status
		deletion_url = self.team_deletion_request.generate_url_for_confirmation()
		res = request_locally_with_host_rewrite(deletion_url, allow_redirects=True)
		self.assertTrue(res.ok)

	def set_roles_to_press_user_only(self, user: str):
		user_doc = frappe.get_doc("User", user)
		user_doc.set("roles", [{"role": "Press User"}])
		user_doc.save()

	def test_team_owner_with_press_user_role_can_request_deletion(self):
		self.set_roles_to_press_user_only(self.team.user)
		frappe.set_user(self.team.user)
		request = request_team_deletion(self.team.name)
		frappe.set_user("Administrator")

		self.assertEqual(request.status, "Pending Verification")

	def test_team_member_who_is_not_owner_cannot_request_deletion(self):
		member = create_test_team().user
		self.set_roles_to_press_user_only(member)
		frappe.set_user(member)
		with self.assertRaisesRegex(frappe.PermissionError, "Team owner to request account deletion"):
			request_team_deletion(self.team.name)
		frappe.set_user("Administrator")

		self.assertFalse(frappe.db.exists("Team Deletion Request", {"team": self.team.name}))

	def test_new_deletion_request_emails_the_press_confirmation_link_to_team_owner(self):
		frappe.set_user(self.team.user)
		request_team_deletion(self.team.name)
		frappe.set_user("Administrator")

		self.sendmail.assert_called_once()
		email = self.sendmail.call_args.kwargs
		self.assertEqual(email["recipients"], self.team.user)
		self.assertEqual(email["template"], "delete_data_confirmation")
		self.assertIn("/api/method/press.api.account.delete_team", email["args"]["link"])

	def test_second_deletion_request_resends_email_instead_of_duplicate_error(self):
		frappe.set_user(self.team.user)
		first = request_team_deletion(self.team.name)
		second = request_team_deletion(self.team.name)
		frappe.set_user("Administrator")

		self.assertEqual(first.name, second.name)
		self.assertEqual(frappe.db.count("Team Deletion Request", {"team": self.team.name}), 1)
		self.assertEqual(self.sendmail.call_count, 2)
