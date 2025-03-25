# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import ipaddress
import typing

import frappe

from press.press.doctype.agent_job.agent_job import handle_polled_job

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


Status = typing.Literal["Running", "Failure", "Success"]


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
	return frappe.db.get_value("Agent Job", {"server": server, "job_id": job_id})


def handle_job_updates(server: str, job_id: str):
	server: Server = frappe.get_doc("Server", server)
	agent = server.agent
	job = frappe.get_value(
		"Agent Job",
		fieldname=["name", "job_id", "status", "callback_failure_count"],
		filters={"job_id": job_id},
		as_dict=True,
	)
	polled_job = agent.get_job_status(job.job_id)
	handle_polled_job(polled_job=polled_job, job=job)


@frappe.whitelist(allow_guest=True)
def callback(job_id: str):
	remote_addr = frappe.request.environ["HTTP_X_FORWARDED_FOR"]
	server = validate_server_request(remote_addr)

	# TODO: There should be something better.
	frappe.set_user("Administrator")

	# Request origin not authorized to update job status.
	if not server:
		return "Invalid request!"

	job = verify_job_id(server, job_id)
	if not job:
		return "Invalid job id!"

	handle_job_updates(server, job_id)
	frappe.set_user("guest")
	return "Success"
