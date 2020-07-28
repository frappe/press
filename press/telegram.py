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
			self.bot = telegram.Bot(token=self.token)
			return self.bot.send_message(
				chat_id=self.chat_id, text=message, parse_mode=self._get_parse_mode(html)
			)
		except Exception:
			log_error("Telegram Bot Error", message=message, html=html)

	def _get_parse_mode(self, html):
		if html:
			return telegram.ParseMode.HTML
		return telegram.ParseMode.MARKDOWN
