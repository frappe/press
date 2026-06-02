# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.static_ip_log.static_ip_log import StaticIPLog, create_static_ip_log
from press.press.doctype.static_ip_plan.test_static_ip_plan import create_test_static_ip_plan
from press.press.doctype.team.test_team import create_test_team


class TestStaticIPLog(FrappeTestCase):
	"""Tests for StaticIPLog document lifecycle hooks and module helpers."""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_press_settings()
		self.team = create_test_team()
		# Server must have provider="AWS EC2" so the log can find a plan
		self.server = create_test_server(team=self.team.name, provider="AWS EC2")
		# A matching enabled plan for the provider
		self.plan = create_test_static_ip_plan(provider="AWS EC2", price_usd=5.0)
		self.static_ip = frappe.mock("ipv4")

	def tearDown(self):
		frappe.db.rollback()

	# ── validate() ─────────────────────────────────────────────────────────

	def test_validate_rejects_invalid_server_type(self):
		"""validate() raises ValidationError for server types outside the allowed set."""
		log = frappe.get_doc(
			{
				"doctype": "Static IP Log",
				"server": self.server.name,
				"server_type": "Proxy Server",  # not in ("Server", "Database Server")
				"static_ip": self.static_ip,
				"status": "Attached",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			log.validate()

	def test_validate_accepts_server_type_server(self):
		"""validate() does NOT raise for server_type 'Server'."""
		log = frappe.get_doc(
			{
				"doctype": "Static IP Log",
				"server": self.server.name,
				"server_type": "Server",
				"static_ip": self.static_ip,
				"status": "Attached",
			}
		)
		log.validate()  # must not raise

	# ── before_insert — invalid status ─────────────────────────────────────

	def test_before_insert_raises_for_unknown_status(self):
		"""before_insert() raises ValidationError for any status other than Attached/Detached."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Static IP Log",
					"server": self.server.name,
					"server_type": "Server",
					"static_ip": self.static_ip,
					"status": "Unknown",
				}
			).insert(ignore_permissions=True)

	# ── Attached flow ───────────────────────────────────────────────────────

	def test_attaching_creates_subscription(self):
		"""Inserting an Attached log auto-creates an enabled Subscription for the server."""
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")

		sub_exists = frappe.db.exists(
			"Subscription",
			{
				"document_type": "Server",
				"document_name": self.server.name,
				"plan_type": "Static IP Plan",
				"enabled": 1,
			},
		)
		self.assertTrue(sub_exists)

	def test_subscription_uses_correct_plan(self):
		"""The auto-created subscription references the provider's Static IP Plan."""
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")

		sub_plan = frappe.db.get_value(
			"Subscription",
			{
				"document_type": "Server",
				"document_name": self.server.name,
				"plan_type": "Static IP Plan",
			},
			"plan",
		)
		self.assertEqual(sub_plan, self.plan.name)

	def test_cannot_attach_already_attached_ip(self):
		"""A second Attached log for the same static_ip raises ValidationError."""
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")

		with self.assertRaises(frappe.ValidationError):
			create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")

	def test_cannot_attach_when_active_subscription_exists(self):
		"""Inserting Attached raises when the server already has an active Static IP subscription."""
		# Manually plant a subscription before touching the log
		frappe.get_doc(
			{
				"doctype": "Subscription",
				"enabled": 1,
				"team": self.team.name,
				"document_type": "Server",
				"document_name": self.server.name,
				"plan_type": "Static IP Plan",
				"plan": self.plan.name,
				"interval": "Daily",
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")

	# ── Detached flow ───────────────────────────────────────────────────────

	def test_detaching_disables_subscription(self):
		"""Inserting a Detached log disables the server's active Static IP subscription."""
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Detached")

		sub_enabled = frappe.db.get_value(
			"Subscription",
			{
				"document_type": "Server",
				"document_name": self.server.name,
				"plan_type": "Static IP Plan",
			},
			"enabled",
		)
		self.assertEqual(sub_enabled, 0)

	def test_detach_without_prior_log_is_allowed(self):
		"""Inserting a Detached log with no prior log succeeds (no subscription is changed)."""
		# _check_if_can_disable_subscription only raises when the last log is already
		# "Detached". A missing log means no guard fires.
		log = create_static_ip_log(self.server.name, "Server", self.static_ip, "Detached")
		self.assertIsNotNone(log.name)

	def test_cannot_detach_already_detached_ip_from_same_server(self):
		"""A second Detached log for the same server+IP raises ValidationError.

		_check_if_can_disable_subscription() sees the last log is "Detached" and
		throws in before_insert — before _disable_subscription is even attempted.
		"""
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")
		create_static_ip_log(self.server.name, "Server", self.static_ip, "Detached")

		with self.assertRaises(frappe.ValidationError):
			create_static_ip_log(self.server.name, "Server", self.static_ip, "Detached")

	# ── Module-level helper ─────────────────────────────────────────────────

	def test_create_static_ip_log_returns_document(self):
		"""create_static_ip_log() inserts and returns a StaticIPLog document."""
		log = create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")
		self.assertIsInstance(log, StaticIPLog)
		self.assertTrue(frappe.db.exists("Static IP Log", log.name))

	def test_create_static_ip_log_stores_correct_fields(self):
		"""The persisted document carries the correct server, server_type and status."""
		log = create_static_ip_log(self.server.name, "Server", self.static_ip, "Attached")
		self.assertEqual(log.server, self.server.name)
		self.assertEqual(log.server_type, "Server")
		self.assertEqual(log.static_ip, self.static_ip)
		self.assertEqual(log.status, "Attached")
