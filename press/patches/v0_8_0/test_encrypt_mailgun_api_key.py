import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import get_decrypted_password

from press.patches.v0_8_0.encrypt_mailgun_api_key import execute


class TestEncryptMailgunApiKey(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_patch_encrypts_plain_mailgun_api_key_and_masks_the_column(self):
		frappe.db.set_single_value("Press Settings", "mailgun_api_key", "plain-key")
		execute()
		self.assertEqual(
			get_decrypted_password("Press Settings", "Press Settings", "mailgun_api_key"), "plain-key"
		)
		self.assertEqual(frappe.db.get_single_value("Press Settings", "mailgun_api_key"), "*" * 9)
