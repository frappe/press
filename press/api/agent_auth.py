import frappe

from press.agent import Agent


def verify_agent(server: str):
	agent_token = frappe.request.headers.get("X-Agent-Token")

	if not agent_token:
		frappe.throw_permission_error()

	agent = Agent(server)
	agent.extract_and_verify_token(agent_token)
