import frappe
from frappe.utils.password import set_encrypted_password

from press.patches.v0_8_0.encrypt_telegram_bot_tokens import is_plain, mask


def execute():
	"""Move the Mailgun API key out of its plain column, now that the field is Password."""
	key = frappe.db.get_single_value("Press Settings", "mailgun_api_key")
	if is_plain(key):
		set_encrypted_password("Press Settings", "Press Settings", key, "mailgun_api_key")
		frappe.db.set_single_value("Press Settings", "mailgun_api_key", mask(key))
