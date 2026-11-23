# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import set_encrypted_password


def create_test_telegram_group(token: str | None = None):
	group = frappe.get_doc(
		{"doctype": "Telegram Group", "name": frappe.mock("name"), "chat_id": "1"}
	).insert()
	if token:
		set_encrypted_password("Telegram Group", group.name, token, "token")
	return group


class TestTelegramGroup(FrappeTestCase):
	pass
