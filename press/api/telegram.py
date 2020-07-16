# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import press.utils
import telebot


@frappe.whitelist(allow_guest=True)
def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""
	if doc.event_type != "invoice.payment_succeeded":
		return

	try:
		event = frappe.parse_json(doc.payload)
		invoice = event["data"]["object"]

		telegram_settings = frappe.get_single("Telegram Notification Settings")
		tb = telebot.TeleBot(telegram_settings.bot_token)
		group_chat_id = telegram_settings.group_chat_id
		message = frappe.render_template(
			telegram_settings.message, context={"invoice": invoice}
		)
		tb.send_message(group_chat_id, message)
	except Exception:
		press.utils.log_error(title="Telegram Notification Failed")
