# Copyright (c) 2025, Frappe and Contributors
# See license.txt
"""
Tests for agent_update/agent_update.py.

Pure helpers and properties are tested without DB round-trips.
before_insert() validation guards are tested with mocked frappe calls.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_update.agent_update import AgentUpdate, bool_to_str

_MODULE = "press.press.doctype.agent_update.agent_update"


# ══════════════════════════════════════════════════════════════════════════════
# bool_to_str
# ══════════════════════════════════════════════════════════════════════════════


class TestBoolToStr(FrappeTestCase):
	def test_true_returns_true_string(self):
		self.assertEqual(bool_to_str(True), "true")

	def test_false_returns_false_string(self):
		self.assertEqual(bool_to_str(False), "false")


# ══════════════════════════════════════════════════════════════════════════════
# AgentUpdate properties — repo_name, repo_owner, agent_repository_url
# ══════════════════════════════════════════════════════════════════════════════


def _update(**kwargs):
	defaults = dict(
		repo="github.com/frappe/agent",
		branch="master",
		commit_hash="abc123",
		restart_web_workers=1,
		restart_rq_workers=1,
		restart_redis=0,
		servers=[],
		agent_startup_timeout_minutes=10,
		run_on_fewer_servers_and_pause=0,
		no_of_servers_to_update_initially=0,
		paused_due_to_test_mode=0,
		stop_after_single_rollback=0,
		status="Pending",
		start=None,
		end=None,
	)
	defaults.update(kwargs)
	doc = SimpleNamespace(**defaults)
	# Bind unbound methods
	doc.repo_name = AgentUpdate.repo_name.fget(doc)
	doc.repo_owner = AgentUpdate.repo_owner.fget(doc)
	doc.agent_repository_url = AgentUpdate.agent_repository_url.fget(doc)
	doc.agent_update_args = AgentUpdate.agent_update_args.fget(doc)
	return doc


class TestAgentUpdateRepoProperties(FrappeTestCase):
	def test_repo_name_extracted_correctly(self):
		doc = SimpleNamespace(repo="github.com/frappe/agent")
		self.assertEqual(AgentUpdate.repo_name.fget(doc), "agent")

	def test_repo_owner_extracted_correctly(self):
		doc = SimpleNamespace(repo="github.com/frappe/agent")
		self.assertEqual(AgentUpdate.repo_owner.fget(doc), "frappe")

	def test_agent_repository_url_built_correctly(self):
		doc = SimpleNamespace(repo="github.com/myorg/my-agent")
		doc.repo_name = AgentUpdate.repo_name.fget(doc)
		doc.repo_owner = AgentUpdate.repo_owner.fget(doc)
		url = AgentUpdate.agent_repository_url.fget(doc)
		self.assertEqual(url, "https://github.com/myorg/my-agent")

	def test_agent_update_args_all_false(self):
		doc = SimpleNamespace(restart_web_workers=0, restart_rq_workers=0, restart_redis=0)
		args = AgentUpdate.agent_update_args.fget(doc)
		self.assertIn("--restart-web-workers=false", args)
		self.assertIn("--restart-rq-workers=false", args)
		self.assertIn("--restart-redis=false", args)

	def test_agent_update_args_all_true(self):
		doc = SimpleNamespace(restart_web_workers=1, restart_rq_workers=1, restart_redis=1)
		args = AgentUpdate.agent_update_args.fget(doc)
		self.assertIn("--restart-web-workers=true", args)
		self.assertIn("--restart-rq-workers=true", args)
		self.assertIn("--restart-redis=true", args)


# ══════════════════════════════════════════════════════════════════════════════
# is_any_update_pending / is_any_ongoing_update
# ══════════════════════════════════════════════════════════════════════════════


def _server(status, agent_status="Active"):
	return SimpleNamespace(status=status, agent_status=agent_status)


class TestAgentUpdatePendingOngoing(FrappeTestCase):
	def test_is_any_update_pending_true(self):
		doc = SimpleNamespace(servers=[_server("Success"), _server("Pending")])
		self.assertTrue(AgentUpdate.is_any_update_pending.fget(doc))

	def test_is_any_update_pending_false(self):
		doc = SimpleNamespace(servers=[_server("Success"), _server("Skipped")])
		self.assertFalse(AgentUpdate.is_any_update_pending.fget(doc))

	def test_is_any_ongoing_update_running(self):
		doc = SimpleNamespace(servers=[_server("Running")])
		self.assertTrue(AgentUpdate.is_any_ongoing_update.fget(doc))

	def test_is_any_ongoing_update_success_but_inactive_agent(self):
		doc = SimpleNamespace(servers=[_server("Success", agent_status="Inactive")])
		self.assertTrue(AgentUpdate.is_any_ongoing_update.fget(doc))

	def test_is_any_ongoing_update_false_when_all_done(self):
		doc = SimpleNamespace(servers=[_server("Success", "Active"), _server("Skipped")])
		self.assertFalse(AgentUpdate.is_any_ongoing_update.fget(doc))


# ══════════════════════════════════════════════════════════════════════════════
# current_agent_update_to_process
# ══════════════════════════════════════════════════════════════════════════════


class TestCurrentAgentUpdateToProcess(FrappeTestCase):
	def test_returns_none_when_no_servers(self):
		doc = SimpleNamespace(servers=[])
		self.assertIsNone(AgentUpdate.current_agent_update_to_process.fget(doc))

	def test_returns_pending_server(self):
		pending = _server("Pending")
		doc = SimpleNamespace(servers=[_server("Success", "Active"), pending])
		result = AgentUpdate.current_agent_update_to_process.fget(doc)
		self.assertIs(result, pending)

	def test_returns_running_server(self):
		running = _server("Running")
		doc = SimpleNamespace(servers=[running, _server("Pending")])
		result = AgentUpdate.current_agent_update_to_process.fget(doc)
		self.assertIs(result, running)

	def test_returns_success_with_inactive_agent(self):
		"""Success+Inactive is still in-progress (waiting for agent to wake up)."""
		in_progress = _server("Success", agent_status="Inactive")
		doc = SimpleNamespace(servers=[in_progress])
		result = AgentUpdate.current_agent_update_to_process.fget(doc)
		self.assertIs(result, in_progress)

	def test_returns_none_when_all_terminated(self):
		doc = SimpleNamespace(servers=[_server("Success", "Active"), _server("Skipped")])
		self.assertIsNone(AgentUpdate.current_agent_update_to_process.fget(doc))


# ══════════════════════════════════════════════════════════════════════════════
# last_terminated_agent_update
# ══════════════════════════════════════════════════════════════════════════════


class TestLastTerminatedAgentUpdate(FrappeTestCase):
	def test_returns_none_when_no_servers(self):
		doc = SimpleNamespace(servers=[])
		self.assertIsNone(AgentUpdate.last_terminated_agent_update.fget(doc))

	def test_returns_last_success_with_active_agent(self):
		first = _server("Success", "Active")
		last = _server("Success", "Active")
		doc = SimpleNamespace(servers=[first, last])
		result = AgentUpdate.last_terminated_agent_update.fget(doc)
		self.assertIs(result, last)

	def test_returns_fatal_server(self):
		fatal = _server("Fatal")
		doc = SimpleNamespace(servers=[_server("Success", "Active"), fatal])
		result = AgentUpdate.last_terminated_agent_update.fget(doc)
		self.assertIs(result, fatal)

	def test_returns_none_when_no_terminated_server(self):
		doc = SimpleNamespace(servers=[_server("Running"), _server("Pending")])
		self.assertIsNone(AgentUpdate.last_terminated_agent_update.fget(doc))


# ══════════════════════════════════════════════════════════════════════════════
# before_insert — validation guards
# ══════════════════════════════════════════════════════════════════════════════


def _before_insert_doc(**kwargs):
	defaults = dict(
		app_server=1,
		database_server=0,
		proxy_server=0,
		restart_web_workers=1,
		restart_rq_workers=1,
		restart_redis=0,
		agent_startup_timeout_minutes=0,
		repo="",
		branch="",
		commit_hash="",
		commit_message="",
		auto_rollback_changes=0,
		rollback_to_specific_commit=0,
		default_rollback_commit="",
		exclude_self_hosted_servers=0,
		servers=[],
		flags=SimpleNamespace(in_group_split=False),
		status="",
	)
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


class TestAgentUpdateBeforeInsert(FrappeTestCase):
	"""before_insert() raises on invalid server/worker configuration."""

	def _run_before_insert(self, doc):
		press_settings = SimpleNamespace(
			agent_repository_owner="frappe",
			branch="master",
		)
		commit_hash = "deadbeef"
		commit_message = "Fix stuff"
		doc.fetch_commit_hash = MagicMock(return_value=commit_hash)
		doc.fetch_commit_message = MagicMock(return_value=commit_message)
		doc.add_server_entries = MagicMock()
		with patch(f"{_MODULE}.frappe.get_single", return_value=press_settings):
			AgentUpdate.before_insert(doc)

	def test_raises_when_no_server_type_selected(self):
		doc = _before_insert_doc(app_server=0, database_server=0, proxy_server=0)
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_no_worker_restart_selected(self):
		doc = _before_insert_doc(restart_web_workers=0, restart_rq_workers=0, restart_redis=0)
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_redis_restart_without_workers(self):
		doc = _before_insert_doc(restart_redis=1, restart_rq_workers=0, restart_web_workers=0)
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_redis_restart_without_web_workers(self):
		doc = _before_insert_doc(restart_redis=1, restart_rq_workers=1, restart_web_workers=0)
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_repo_starts_with_https(self):
		doc = _before_insert_doc(repo="https://github.com/frappe/agent")
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_repo_starts_with_http(self):
		doc = _before_insert_doc(repo="http://github.com/frappe/agent")
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_raises_when_rollback_commit_hash_missing(self):
		doc = _before_insert_doc(
			auto_rollback_changes=1,
			rollback_to_specific_commit=1,
			default_rollback_commit="",
		)
		with self.assertRaises(frappe.ValidationError):
			self._run_before_insert(doc)

	def test_sets_default_timeout_when_zero(self):
		doc = _before_insert_doc(agent_startup_timeout_minutes=0)
		self._run_before_insert(doc)
		self.assertEqual(doc.agent_startup_timeout_minutes, 10)

	def test_sets_default_repo_from_press_settings(self):
		doc = _before_insert_doc(repo="")
		self._run_before_insert(doc)
		self.assertIn("frappe/agent", doc.repo)

	def test_skips_all_validation_in_group_split(self):
		"""in_group_split flag bypasses before_insert entirely."""
		doc = _before_insert_doc(
			flags=SimpleNamespace(in_group_split=True),
			app_server=0,
			database_server=0,
			proxy_server=0,
		)
		# Should not raise even with invalid config
		AgentUpdate.before_insert(doc)


# ══════════════════════════════════════════════════════════════════════════════
# is_commit_supported
# ══════════════════════════════════════════════════════════════════════════════


class TestIsCommitSupported(FrappeTestCase):
	def test_commit_after_cutoff_is_supported(self):
		doc = SimpleNamespace()
		doc.fetch_commit_date = MagicMock(return_value=datetime.datetime(2025, 5, 1, 0, 0, 0))
		self.assertTrue(AgentUpdate.is_commit_supported(doc, "newcommit"))

	def test_commit_before_cutoff_is_not_supported(self):
		doc = SimpleNamespace()
		doc.fetch_commit_date = MagicMock(return_value=datetime.datetime(2025, 1, 1, 0, 0, 0))
		self.assertFalse(AgentUpdate.is_commit_supported(doc, "oldcommit"))

	def test_commit_with_none_date_is_not_supported(self):
		doc = SimpleNamespace()
		doc.fetch_commit_date = MagicMock(return_value=None)
		self.assertFalse(AgentUpdate.is_commit_supported(doc, "unknowncommit"))
