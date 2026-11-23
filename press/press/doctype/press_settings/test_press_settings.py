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
