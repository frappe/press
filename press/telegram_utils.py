# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
import requests
from frappe.utils import get_url
from frappe.utils.password import get_decrypted_password

from press.utils import log_error

API_URL = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE_LENGTH = 4096


class TelegramError(Exception):
	pass


class NetworkError(TelegramError):
	"""A failure that can go away on retry, like a timeout or a server error"""


class RetryAfter(TelegramError):
	def __init__(self, retry_after: int):
		super().__init__(f"Flood control exceeded. Retry in {retry_after} seconds")
		self.retry_after = retry_after


class Telegram:
	def __init__(self, topic: str | None = None, group: str | None = None):
		self.group = group or frappe.db.get_single_value("Press Settings", "telegram_alerts_chat_group")
		self.chat_id = frappe.db.get_value("Telegram Group", self.group, "chat_id")
		self.token = self.get_token()
		self.topic = topic
		self.topic_id = frappe.db.get_value(
			"Telegram Group Topic", {"parent": self.group, "topic": topic}, "topic_id"
		)

	def get_token(self) -> str | None:
		if self.group and (
			token := get_decrypted_password("Telegram Group", self.group, "token", raise_exception=False)
		):
			return token
		return get_decrypted_password(
			"Press Settings", "Press Settings", "telegram_bot_token", raise_exception=False
		)

	def send(self, message, html=False, reraise=False):
		if not message:
			return None
		try:
			return self.call(
				"sendMessage",
				chat_id=self.chat_id,
				text=message[:MAX_MESSAGE_LENGTH],
				parse_mode="HTML" if html else "Markdown",
				message_thread_id=self.topic_id,
			)
		except Exception:
			if reraise:
				raise
			log_error(
				"Telegram Bot Error",
				message=message,
				html=html,
				chat_id=self.chat_id,
				topic_id=self.topic_id,
			)

	def call(self, method: str, **parameters):
		"""Call a Telegram Bot API method and return its result"""
		parameters = {key: value for key, value in parameters.items() if value is not None}
		try:
			response = requests.post(
				API_URL.format(token=self.token, method=method), json=parameters, timeout=3
			)
		except requests.RequestException as e:
			# The URL in the error holds the bot token
			raise NetworkError(str(e).replace(self.token or "<token>", "<token>")) from None
		return parse_response(response)

	@property
	def username(self) -> str:
		return self.call("getMe")["username"]

	def set_webhook(self, secret_token: str):
		url = get_url("/api/method/press.api.telegram.hook")
		self.call("setWebhook", url=url, secret_token=secret_token)

	def respond(self, message):
		if not message:
			return

		# Only respond to message from the Telegram alerts group
		if self.chat_id != str(message["chat"]["id"]):
			return

		# Respond on the same topic
		self.topic_id = message.get("message_thread_id")

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
		if mention != f"@{self.username}":
			return

		command = text.replace(mention, "")
		response = self.process(command.strip())
		if response:
			self.send(response)

	def process(self, command):
		arguments = command.split(" ")

		if len(arguments) >= 4 and frappe.unscrub(arguments[0]) not in ALLOWED_DOCTYPES:
			return show_help_message()
		if len(arguments) == 1:
			commands = {
				"help": show_help_message,
				"ping": frappe.ping,
			}
			return commands.get(arguments[0], what)(*arguments[1:])
		if len(arguments) == 4:
			doctype, name, action, key = arguments
			commands = {"get": get_value, "execute": execute}
			return commands.get(action, what)(frappe.unscrub(doctype), name, key)
		if len(arguments) >= 5:
			doctype, name, action, key, *values = arguments
			commands = {
				"set": set_value,
				"execute": execute,
			}
			if action == "set" and len(values) == 1:
				return commands.get(action, what)(frappe.unscrub(doctype), name, key, values[0])
			return commands.get(action, what)(frappe.unscrub(doctype), name, key, *values)
		return what()


def parse_response(response: requests.Response):
	"""Raise like python-telegram-bot 13 did, so callers keep their retry rules"""
	try:
		data = response.json()
	except ValueError:
		data = {}
	if data.get("ok"):
		return data["result"]
	if retry_after := (data.get("parameters") or {}).get("retry_after"):
		raise RetryAfter(retry_after)
	description = f"{data.get('description', 'Unknown error')} ({response.status_code})"
	if response.status_code in (401, 403, 404, 409):
		raise TelegramError(description)
	raise NetworkError(description)


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
	if method == "get_password":
		return "Reading passwords is not allowed"
	try:
		document = frappe.get_doc(doctype, name)
		return document.run_method(method, *args)
	except Exception:
		return f"```{frappe.get_traceback()}```"


def show_help_message(*args):
	return HELP_MESSAGE


def what(*args):
	return "What are you talking about?"


ALLOWED_DOCTYPES = ("Site", "Bench", "Server", "Proxy Server", "Database Server")

HELP_MESSAGE = """Try one of these

doctype name execute method
doctype name get field
doctype name set field value
doctype name execute method argument1 argument2 ...

doctype = site|bench|server|proxy-server|database-server

```
server f17.frappe.cloud execute reboot```
```
site docs.frappe.cloud get status```
```
bench docs.frappe.cloud set auto_scale_workers 0```
```
server f17.frappe.cloud execute increase_disk_size 25```
"""
