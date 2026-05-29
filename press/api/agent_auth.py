import base64
import json
from typing import TYPE_CHECKING

import frappe
from frappe.rate_limiter import rate_limit

from press.agent import Agent

if TYPE_CHECKING:
	from press.press.doctype.server.server import BaseServer


def extract_server_from_token(token: str):
	try:
		parts = token.split(".")

		if len(parts) != 3:
			return None

		payload_b64 = parts[1]

		# fix padding
		payload_b64 += "=" * (-len(payload_b64) % 4)

		payload = json.loads(base64.urlsafe_b64decode(payload_b64))

		return payload.get("server"), payload.get("server_type")

	except Exception:
		return None


def verify_agent():
	agent_token = frappe.request.headers.get("X-Agent-Token")

	if not agent_token:
		frappe.throw_permission_error()

	token_data = extract_server_from_token(agent_token)

	if not token_data:
		frappe.throw_permission_error()

	server, server_type = token_data

	agent = Agent(server)
	agent.extract_and_verify_token(agent_token)

	return server, server_type


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60)
def regenerate_token():
	server, server_type = verify_agent()

	doc: BaseServer = frappe.get_doc(server_type, server)

	secret = doc._generate_secret()
	return doc.sign_agent_token(secret)
