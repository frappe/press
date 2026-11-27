# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.press_settings.press_settings import PressSettings
from press.telegram_utils import Telegram


def create_test_press_settings():
	"""Create test press settings doc"""
	create_test_cluster()
	if not frappe.db.exists("TLS Certificate", "*.fc.dev"):
		frappe.get_doc(
			{
				"doctype": "TLS Certificate",
				"name": "*.fc.dev",
				"domain": "fc.dev",
				"wildcard": True,
				"status": "Active",
				"rsa_key_size": 2048,
			}
		).db_insert()

	frappe.get_doc(
		{
			"doctype": "Root Domain",
			"name": "fc.dev",
			"dns_provider": "AWS Route 53",
			"default_cluster": "Default",
			"aws_access_key_id": frappe.mock("password"),
			"aws_secret_access_key": frappe.mock("password"),
		}
	).insert(ignore_if_duplicate=True)

	settings = frappe.get_single("Press Settings")
	settings.domain = "fc.dev"
	settings.bench_configuration = "{}"
	settings.rsa_key_size = 2048
	settings.certbot_directory = ".certbot"
	settings.eff_registration_email = frappe.mock("email")
	settings.max_concurrent_physical_restorations = 2
	settings.minimum_rebuild_memory = 2
	# Offsite backups read these on every Site Backup insert. Without them
	# get_password raises, which fails any test that creates a backup.
	settings.offsite_backups_access_key_id = frappe.mock("password")
	settings.offsite_backups_secret_access_key = frappe.mock("password")
	settings.save()
	return settings


def get_telegram_webhook_secret():
	return get_decrypted_password(
		"Press Settings", "Press Settings", "telegram_webhook_secret", raise_exception=False
	)


class TestPressSettings(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch.object(Telegram, "set_webhook")
	def test_set_telegram_webhook_stores_the_secret_it_registers(self, set_webhook: Mock):
		PressSettings("Press Settings", "Press Settings").set_telegram_webhook()
		set_webhook.assert_called_once_with(get_telegram_webhook_secret())

	@patch.object(Telegram, "set_webhook")
	def test_set_telegram_webhook_ignores_invalid_unsaved_settings(self, set_webhook: Mock):
		settings = PressSettings("Press Settings", "Press Settings")
		settings.minimum_rebuild_memory = 1
		settings.set_telegram_webhook()
		set_webhook.assert_called_once_with(get_telegram_webhook_secret())

	@patch.object(Telegram, "set_webhook", new=Mock())
	def test_settings_save_after_set_telegram_webhook_keeps_the_secret(self):
		create_test_press_settings()
		PressSettings("Press Settings", "Press Settings").set_telegram_webhook()
		secret = get_telegram_webhook_secret()
		create_test_press_settings()
		self.assertEqual(get_telegram_webhook_secret(), secret)


class TestPressSettingsProductionServerIPs(FrappeTestCase):
	def setUp(self):
		super().setUp()
		create_test_press_settings()
		self.settings = frappe.get_doc("Press Settings")

	def tearDown(self):
		frappe.db.rollback()

	def test_a_value_that_is_not_an_ip_is_refused(self):
		self.settings.production_server_ip = "203.0.113.7\nnot-an-ip"
		with self.assertRaises(frappe.ValidationError):
			self.settings.save()

	@patch("press.press.doctype.press_settings.press_settings.frappe.enqueue")
	def test_a_new_production_ip_syncs_the_firewalls(self, enqueue: Mock):
		self.settings.production_server_ip = "203.0.113.7\n203.0.113.8"
		self.settings.save()

		enqueue.assert_called_once()
		self.assertEqual(
			enqueue.call_args.args[0],
			"press.press.doctype.server_firewall.server_firewall.sync_enabled_firewalls",
		)

	@patch("press.press.doctype.press_settings.press_settings.frappe.enqueue")
	def test_creating_the_settings_does_not_sync_the_firewalls(self, enqueue: Mock):
		"""The installer creates the settings before any queue runs, as `init_singles` does here."""
		settings = frappe.new_doc("Press Settings")
		settings.production_server_ip = "203.0.113.7"
		settings.flags.ignore_mandatory = True
		settings.flags.ignore_validate = True
		settings.save()

		enqueue.assert_not_called()

	@patch("press.press.doctype.press_settings.press_settings.frappe.enqueue")
	def test_a_save_without_an_ip_change_does_not_sync_the_firewalls(self, enqueue: Mock):
		self.settings.save()

		enqueue.assert_not_called()
