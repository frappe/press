# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for github_webhook_log/github_webhook_log.py.

get_repository_details_from_payload() is a pure function — no DB needed.
handle_events() dispatch logic is tested with mocked method calls.
handle_installation_event() action routing is tested with mocked payloads.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.github_webhook_log.github_webhook_log import (
	GitHubWebhookLog,
	get_repository_details_from_payload,
)

_MODULE = "press.press.doctype.github_webhook_log.github_webhook_log"

# ══════════════════════════════════════════════════════════════════════════════
# get_repository_details_from_payload — pure function
# ══════════════════════════════════════════════════════════════════════════════


class TestGetRepositoryDetailsFromPayload(FrappeTestCase):
	"""get_repository_details_from_payload() extracts repo name and owner from various payload shapes."""

	def test_standard_push_payload(self):
		"""Standard push payload has repository.name and repository.owner.login."""
		payload = {
			"repository": {
				"name": "frappe",
				"owner": {"login": "frappe"},
			}
		}
		result = get_repository_details_from_payload(payload)
		self.assertEqual(result["name"], "frappe")
		self.assertEqual(result["owner"], "frappe")

	def test_installation_payload_with_single_repo(self):
		"""Installation event with a single repositories_added entry."""
		payload = {
			"repositories_added": [{"name": "myapp", "full_name": "frappe/myapp"}],
			"installation": {"account": {"login": "frappe"}},
		}
		result = get_repository_details_from_payload(payload)
		self.assertEqual(result["name"], "myapp")
		self.assertEqual(result["owner"], "frappe")

	def test_owner_from_full_name_when_login_absent(self):
		"""Owner is extracted from the full_name when login is absent in repositories_added."""
		payload = {
			"repositories_added": [{"name": "repo1", "full_name": "acme-corp/repo1"}],
		}
		result = get_repository_details_from_payload(payload)
		self.assertEqual(result["owner"], "acme-corp")

	def test_owner_from_installation_account_when_repo_owner_absent(self):
		"""Falls back to installation.account.login when repository.owner is absent."""
		payload = {
			"repository": {"name": "myrepo"},
			"installation": {"account": {"login": "fallback-org"}},
		}
		result = get_repository_details_from_payload(payload)
		self.assertEqual(result["owner"], "fallback-org")

	def test_empty_payload_returns_none_values(self):
		"""An empty payload returns {'name': None, 'owner': None}."""
		result = get_repository_details_from_payload({})
		self.assertIsNone(result["name"])
		self.assertIsNone(result["owner"])

	def test_multi_repo_installation_has_no_single_repo_name(self):
		"""When repositories_added has > 1 entry, repo name is not extracted from it."""
		payload = {
			"repositories_added": [
				{"name": "repo-a", "full_name": "org/repo-a"},
				{"name": "repo-b", "full_name": "org/repo-b"},
			],
			"installation": {"account": {"login": "org"}},
		}
		result = get_repository_details_from_payload(payload)
		# name should be None — more than one repo so the "len == 1" guard fails
		self.assertIsNone(result["name"])
		# owner should still come from installation.account.login
		self.assertEqual(result["owner"], "org")


# ══════════════════════════════════════════════════════════════════════════════
# GitHubWebhookLog.handle_events — dispatch
# ══════════════════════════════════════════════════════════════════════════════


class TestGitHubWebhookLogHandleEvents(FrappeTestCase):
	"""handle_events() dispatches to the correct handler based on self.event."""

	def _doc(self, event: str):
		doc = MagicMock(spec=GitHubWebhookLog)
		doc.event = event
		doc.handle_events = GitHubWebhookLog.handle_events.__get__(doc, GitHubWebhookLog)
		return doc

	def test_push_event_dispatches_to_handle_push_event(self):
		doc = self._doc("push")
		with patch(f"{_MODULE}.frappe.db.commit"):
			doc.handle_events()
		doc.handle_push_event.assert_called_once()

	def test_installation_event_dispatches_to_handle_installation_event(self):
		doc = self._doc("installation")
		with patch(f"{_MODULE}.frappe.db.commit"):
			doc.handle_events()
		doc.handle_installation_event.assert_called_once()

	def test_installation_repositories_dispatches_correctly(self):
		doc = self._doc("installation_repositories")
		with patch(f"{_MODULE}.frappe.db.commit"):
			doc.handle_events()
		doc.handle_repository_installation_event.assert_called_once()

	def test_unknown_event_does_not_raise(self):
		doc = self._doc("unknown_event")
		with patch(f"{_MODULE}.frappe.db.commit"):
			doc.handle_events()  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# GitHubWebhookLog.handle_installation_event — action routing
# ══════════════════════════════════════════════════════════════════════════════


class TestGitHubWebhookLogHandleInstallationEvent(FrappeTestCase):
	"""handle_installation_event() routes 'created'/'unsuspend' to created handler."""

	def _make_doc_with_payload(self, action: str):
		doc = MagicMock(spec=GitHubWebhookLog)
		doc.get_parsed_payload = lambda: frappe._dict(
			{"action": action, "installation": {"account": {"login": "org"}}}
		)
		doc.handle_installation_event = GitHubWebhookLog.handle_installation_event.__get__(
			doc, GitHubWebhookLog
		)
		return doc

	def test_created_action_calls_handle_installation_created(self):
		doc = self._make_doc_with_payload("created")
		doc.handle_installation_event()
		doc.handle_installation_created.assert_called_once()
		doc.handle_installation_deletion.assert_not_called()

	def test_unsuspend_action_calls_handle_installation_created(self):
		doc = self._make_doc_with_payload("unsuspend")
		doc.handle_installation_event()
		doc.handle_installation_created.assert_called_once()

	def test_deleted_action_calls_handle_installation_deletion(self):
		doc = self._make_doc_with_payload("deleted")
		doc.handle_installation_event()
		doc.handle_installation_deletion.assert_called_once()
		doc.handle_installation_created.assert_not_called()

	def test_suspend_action_calls_handle_installation_deletion(self):
		doc = self._make_doc_with_payload("suspend")
		doc.handle_installation_event()
		doc.handle_installation_deletion.assert_called_once()
