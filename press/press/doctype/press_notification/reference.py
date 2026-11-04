# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Find the Site, Release Group or Server a notification is about, so Press Roles can filter it."""

from __future__ import annotations

from typing import Any

import frappe

# The Agent Job rule lives in `agent_job_reference`; the backfill patch reuses this table.
REFERENCE_FIELDS = {
	"Deploy Candidate": ("Release Group", "group"),
	"Deploy Candidate Build": ("Release Group", "group"),
	"Release Pipeline": ("Release Group", "release_group"),
	"Auto Scale Record": ("Server", "primary_server"),
	"NFS Volume Attachment": ("Server", "primary_server"),
	"NFS Volume Detachment": ("Server", "primary_server"),
}


def find_reference(document_type: str, document_name: str):
	# MariaDB casts names to 0 for `name = 0`, so a lookup would match another team's document
	if not document_name:
		return None, None
	if document_type == "Agent Job":
		return agent_job_reference(document_name)
	if document_type in REFERENCE_FIELDS:
		reference_doctype, field = REFERENCE_FIELDS[document_type]
		if reference_name := frappe.db.get_value(document_type, document_name, field):
			return reference_doctype, reference_name
	return None, None


def agent_job_reference(name: str):
	job: Any = frappe.db.get_value(
		"Agent Job", name, ["site", "bench", "server_type", "server"], as_dict=True
	)
	if not job:
		return None, None
	if job.site:
		return "Site", job.site
	if job.bench and (group := frappe.db.get_value("Bench", job.bench, "group")):
		return "Release Group", group
	return job.server_type, job.server
