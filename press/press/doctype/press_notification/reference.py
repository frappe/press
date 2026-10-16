# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Find the Site, Release Group or Server a notification is about, so Press Roles can filter it."""

from __future__ import annotations

import frappe

RELEASE_GROUP_FIELDS = {
	"Deploy Candidate": "group",
	"Deploy Candidate Build": "group",
	"Release Pipeline": "release_group",
}


def find_reference(document_type: str, document_name: str):
	if document_type == "Agent Job":
		return agent_job_reference(document_name)
	if document_type in RELEASE_GROUP_FIELDS:
		field = RELEASE_GROUP_FIELDS[document_type]
		return "Release Group", frappe.db.get_value(document_type, document_name, field)
	if document_type == "Auto Scale Record":
		return "Server", frappe.db.get_value(document_type, document_name, "primary_server")
	return None, None


def agent_job_reference(name: str):
	job = frappe.db.get_value("Agent Job", name, ["site", "bench", "server_type", "server"], as_dict=True)
	if not job:
		return None, None
	if job.site:
		return "Site", job.site
	if job.bench:
		return "Release Group", frappe.db.get_value("Bench", job.bench, "group")
	return job.server_type, job.server
