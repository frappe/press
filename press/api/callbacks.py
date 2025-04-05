# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import ipaddress
import typing

import frappe

from press.press.doctype.agent_job.agent_job import handle_polled_job
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.server.server import Server


def check_ip_version(remote_addr: str):
	try:
		return ipaddress.ip_interface(remote_addr).version
	except ValueError:
		return None


def validate_server_request(remote_addr: str):
	version = check_ip_version(remote_addr)

	if version == 4:
		server = frappe.get_value("Server", {"ip": remote_addr})
	elif version == 6:
		# Added this here, however fc does not support ipv6
		remote_addr = f"{remote_addr.split('::')[0]}::"
		server = frappe.get_value("Server", {"ipv6": remote_addr})
	else:
		server = None

	return server


def verify_job_id(server: str, job_id: str):
	return frappe.get_value("Agent Job", {"server": server, "job_id": job_id})


def handle_job_updates(server: str, job_identifier: str):
	current_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		job_id = job_identifier
		server: Server = frappe.get_doc("Server", server)
		agent = server.agent
		press_settings: PressSettings = frappe.get_doc("Press Settings")

		if not press_settings.use_agent_job_callbacks or not server.use_agent_job_callbacks:
			return

		# For some reason output is not returned when job returns from rq callback
		polled_job = agent.get_job_status(job_id)

		job = frappe.get_value(
			"Agent Job",
			fieldname=[
				"name",
				"job_id",
				"status",
				"callback_failure_count",
				"job_type",
			],
			filters={"job_id": job_id},
			as_dict=True,
		)

		callback = frappe.get_doc(
			{
				"doctype": "Agent Job Callback",
				"job_name": job.job_type,
				"agent_job": polled_job["agent_job_id"],
				"status": polled_job["status"],
			}
		)
		callback.insert()
		frappe.db.commit()

		handle_polled_job(polled_job=polled_job, job=job)
	except Exception as e:
		log_error("Failed to process agent job callback", data=e)
		raise
	finally:
		frappe.set_user(current_user)


@frappe.whitelist(allow_guest=True)
def callback(job_id: str):
	"""
	Handle job updates sent from agent.
	"""
	remote_addr = frappe.request.environ["HTTP_X_FORWARDED_FOR"]
	server = validate_server_request(remote_addr)

	# TODO: There should be something better.

	# Request origin not authorized to update job status.
	if not server:
		frappe.throw("Not permitted", frappe.ValidationError)

	job = verify_job_id(server, job_id)
	if not job:
		frappe.throw("Invalid Job Id", frappe.ValidationError)

	frappe.enqueue(handle_job_updates, server=server, job_identifier=job_id)
