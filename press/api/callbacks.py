# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import ipaddress
import typing

import frappe

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


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


def update_status(job: str, status: Status):
	agent_job: AgentJob = frappe.get_doc("Agent Job", job)

	agent_job.status = status
	agent_job.save(ignore_permissions=True)

	frappe.db.commit()
	return {"status": agent_job.status}


@frappe.whitelist(allow_guest=True)
def callback(job_id: str, status: Status):
	remote_addr = frappe.request.environ["HTTP_X_FORWARDED_FOR"]
	server = validate_server_request(remote_addr)

	# Request origin not authorized to update job status.
	if not server:
		return "Invalid request!"

	job = verify_job_id(server, job_id)
	if not job:
		return "Invalid job id!"

	return update_status(job, status)
