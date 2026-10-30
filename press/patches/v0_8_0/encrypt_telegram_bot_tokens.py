from typing import TypeGuard

import frappe
from frappe.utils.password import set_encrypted_password


def execute():
	"""Move the bot tokens out of their plain columns, now that the fields are Password."""
	token = frappe.db.get_single_value("Press Settings", "telegram_bot_token")
	if is_plain(token):
		set_encrypted_password("Press Settings", "Press Settings", token, "telegram_bot_token")
		frappe.db.set_single_value("Press Settings", "telegram_bot_token", mask(token))

	for group in frappe.get_all("Telegram Group", fields=["name", "token"]):
		if is_plain(group.token):
			set_encrypted_password("Telegram Group", group.name, group.token, "token")
			frappe.db.set_value(
				"Telegram Group", group.name, "token", mask(group.token), update_modified=False
			)


def is_plain(value: object) -> TypeGuard[str]:
	return isinstance(value, str) and value != "" and set(value) != {"*"}


def mask(value: str) -> str:
	return "*" * len(value)
