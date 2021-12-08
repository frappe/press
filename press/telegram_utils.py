# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import telegram
from press.utils import log_error


class Telegram:
	def __init__(self):
		self.token, self.chat_id = frappe.db.get_value(
			"Press Settings", None, ["telegram_bot_token", "telegram_chat_id"]
		)

	def send(self, message, html=False):
		try:
			text = message[: telegram.MAX_MESSAGE_LENGTH]
			parse_mode = self._get_parse_mode(html)
			return self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=parse_mode)
		except Exception:
			log_error("Telegram Bot Error", message=message, html=html)

	def _get_parse_mode(self, html):
		if html:
			return telegram.ParseMode.HTML
		return telegram.ParseMode.MARKDOWN

	@property
	def bot(self):
		return telegram.Bot(token=self.token)

	def respond(self, message):
		self.chat_id = frappe.db.get_single_value("Press Settings", "telegram_alert_chat_id")

		# Only respond to message from the Telegram alerts group
		if self.chat_id != str(message["chat"]["id"]):
			return

		text = message["text"]
		entities = message.get("entities", [])
		# Ignore pointless chatter
		if not entities or entities[0]["type"] != "mention":
			return

		entity = entities[0]
		begin = entity["offset"]
		end = entity["offset"] + entity["length"]

		mention = text[begin:end]
		# Only respond to messages mentioning the bot
		if mention != f"@{self.bot.username}":
			return

		command = text.replace(mention, "")
		response = self.process(command.strip())
		self.send(response)

	def process(self, command):
		arguments = command.split(" ")

		if len(arguments) == 1:
			commands = {
				"help": show_help_message,
				"ping": frappe.ping,
			}
			return commands.get(arguments[0], what)(*arguments[1:])
		elif len(arguments) == 4:
			doctype, name, action, key = arguments
			commands = {"get": get_value, "execute": execute}
			return commands.get(action, what)(frappe.unscrub(doctype), name, key)
		elif len(arguments) == 5:
			doctype, name, action, key, value = arguments
			commands = {
				"set": set_value,
			}
			return commands.get(action, what)(frappe.unscrub(doctype), name, key, value)
		return what()


def set_value(doctype, name, field, value, *args):
	try:
		document = frappe.get_doc(doctype, name)
		document.set(field, value)
		document.save()
	except Exception:
		return f"```{frappe.get_traceback()}```"


def get_value(doctype, name, field, *args):
	try:
		return frappe.db.get_value(doctype, name, field)
	except Exception:
		return f"```{frappe.get_traceback()}```"


def execute(doctype, name, method, *args):
	# return "EXECUTE", doctype, name, method
	try:
		document = frappe.get_doc(doctype, name)
		return document.run_method(method)
	except Exception:
		return f"```{frappe.get_traceback()}```"


def show_help_message(*args):
	return HELP_MESSAGE


def what(*args):
	return "What are you talking about?"


HELP_MESSAGE = """Try one of these

doctype name execute method
doctype name get field
doctype name set field value

doctype = site|bench|server|proxy-server|database-server

```
server f17.frappe.cloud execute reboot```
```
site docs.frappe.cloud get status```
```
bench docs.frappe.cloud set auto_scale_workers 0```
"""
