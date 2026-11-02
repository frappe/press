import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

from press.patches.v0_8_0.encrypt_telegram_bot_tokens import execute
from press.press.doctype.telegram_group.test_telegram_group import create_test_telegram_group


class TestEncryptTelegramBotTokens(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_patch_encrypts_plain_press_settings_token_and_masks_the_column(self):
		frappe.db.set_single_value("Press Settings", "telegram_bot_token", "plain-token")
		execute()
		self.assertEqual(
			get_decrypted_password("Press Settings", "Press Settings", "telegram_bot_token"), "plain-token"
		)
		self.assertEqual(frappe.db.get_single_value("Press Settings", "telegram_bot_token"), "*" * 11)

	def test_patch_encrypts_plain_group_token_and_masks_the_column(self):
		group = create_test_telegram_group()
		frappe.db.set_value("Telegram Group", group.name, "token", "plain-token")
		execute()
		self.assertEqual(get_decrypted_password("Telegram Group", group.name, "token"), "plain-token")
		self.assertEqual(frappe.db.get_value("Telegram Group", group.name, "token"), "*" * 11)

	def test_patch_keeps_token_that_is_already_encrypted(self):
		group = create_test_telegram_group(token="secret-token")
		frappe.db.set_value("Telegram Group", group.name, "token", "*" * 12)
		execute()
		self.assertEqual(get_decrypted_password("Telegram Group", group.name, "token"), "secret-token")
