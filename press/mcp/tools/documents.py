# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from typing import Any

import frappe
from frappe.model import default_fields as FRAPPE_DEFAULT_FIELDS

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.utils import system_manager_only

DOCTYPES: dict[str, dict[str, Any]] = {
	"Cluster": {
		"filters": ["name", "status", "cloud_provider", "team"],
		"default_fields": ["title", "status", "cloud_provider", "region", "team"],
		"context": "Use for server placement and provider/region scope.",
	},
	"Server": {
		"filters": ["status", "cluster", "team", "database_server"],
		"links": {"cluster": "Cluster", "database_server": "Database Server"},
		"default_fields": ["title", "status", "cluster", "team", "plan", "database_server"],
		"context": "Use with Bench/Site for hosting; Agent Job for operations.",
	},
	"Database Server": {
		"filters": ["status", "cluster", "team", "primary"],
		"default_fields": ["title", "status", "cluster", "team", "plan", "primary"],
		"context": "Use from Server.database_server for DB health/topology.",
	},
	"Proxy Server": {
		"filters": ["status", "cluster", "team"],
		"default_fields": ["status", "cluster", "team", "domain", "primary", "is_ssh_proxy_setup"],
		"context": "Use for routing, SSH proxy, and proxy setup checks.",
	},
	"Ansible Play": {
		"filters": ["server", "server_type", "status", "play"],
		"links": {"server": ["Server", "Database Server", "Proxy Server"]},
		"default_fields": ["server_type", "server", "play", "status", "start", "end", "duration"],
		"context": "Use for server-side automation timeline; tasks show step output.",
	},
	"Ansible Task": {
		"filters": ["play", "status", "task", "role"],
		"links": {"play": "Ansible Play"},
		"default_fields": ["play", "task", "role", "status", "start", "end", "duration"],
		"context": "Use for failed Ansible step; full doc has output/error.",
	},
	"Site": {
		"filters": ["status", "domain", "bench", "group", "server", "team"],
		"links": {"server": "Server", "bench": "Bench", "group": "Release Group", "cluster": "Cluster"},
		"default_fields": ["status", "team", "server", "bench", "group", "plan", "host_name"],
		"context": "Use with Bench/Release Group for version; Agent Job for failures.",
	},
	"Site Domain": {
		"filters": ["site", "domain", "status", "dns_type", "team"],
		"links": {"site": "Site"},
		"default_fields": ["site", "domain", "status", "dns_type", "redirect_to_primary", "retry_count"],
		"context": "Use for DNS/TLS/routing issues for a site.",
	},
	"Site Backup": {
		"filters": ["site", "status", "physical", "offsite"],
		"links": {"site": "Site", "job": "Agent Job"},
		"default_fields": ["site", "status", "job", "physical", "offsite", "files_availability"],
		"context": "Use for restore points; check job and file availability.",
	},
	"Site Update": {
		"filters": ["site", "status", "group", "source_bench", "destination_bench"],
		"links": {
			"site": "Site",
			"source_bench": "Bench",
			"destination_bench": "Bench",
			"update_job": "Agent Job",
			"recover_job": "Agent Job",
		},
		"default_fields": [
			"site",
			"status",
			"source_bench",
			"destination_bench",
			"deploy_type",
			"update_job",
		],
		"query_examples": [{"site": "<site-name>"}, {"status": "Failure"}],
		"context": "Use for update status; inspect update/recover Agent Jobs.",
	},
	"Site Action": {
		"filters": ["site", "status", "action_type", "team"],
		"links": {"site": "Site", "destination_bench": "Bench"},
		"default_fields": ["site", "action_type", "status", "scheduled_time", "start", "end", "duration"],
		"context": "Use for site operation timeline; steps show nested actions.",
	},
	"Site Action Step": {
		"filters": ["parent", "status", "reference_doctype", "reference_name"],
		"links": {
			"parent": "Site Action",
			"reference_name": ["Agent Job", "Site Update", "Site Migration", "Physical Backup Restoration"],
		},
		"default_fields": ["parent", "step", "status", "reference_doctype", "reference_name", "duration"],
		"context": "Use for site action stage failures and linked records.",
	},
	"Site Activity": {
		"filters": ["site", "action", "team", "job"],
		"links": {"site": "Site", "job": "Agent Job"},
		"default_fields": ["site", "action", "reason", "team", "job", "creation"],
		"context": "Use for human-readable site timeline and reasons.",
	},
	"Site Migration": {
		"filters": ["site", "status", "migration_type", "source_server", "destination_server"],
		"links": {
			"site": "Site",
			"source_bench": "Bench",
			"destination_bench": "Bench",
			"source_server": "Server",
			"destination_server": "Server",
			"backup": "Site Backup",
		},
		"default_fields": [
			"site",
			"status",
			"migration_type",
			"source_server",
			"destination_server",
			"backup",
		],
		"query_examples": [{"site": "<site-name>"}, {"status": "Failure"}],
		"context": "Use for move path between benches, servers, or clusters.",
	},
	"Site Migration Step": {
		"filters": ["parent", "status", "step_job"],
		"links": {"parent": "Site Migration", "step_job": "Agent Job"},
		"default_fields": ["parent", "step_title", "status", "step_job", "method_name"],
		"context": "Use for migration stage and linked Agent Job.",
	},
	"Bench": {
		"filters": ["status", "server", "database_server", "group", "cluster", "team"],
		"links": {
			"server": "Server",
			"database_server": "Database Server",
			"group": "Release Group",
			"cluster": "Cluster",
			"candidate": "Deploy Candidate",
		},
		"default_fields": ["status", "server", "database_server", "group", "cluster", "candidate"],
		"context": "Use with Site for hosting and Release Group for version.",
	},
	"Deploy": {
		"filters": ["group", "candidate", "team", "staging"],
		"links": {"group": "Release Group", "candidate": "Deploy Candidate"},
		"default_fields": ["group", "candidate", "team", "staging", "creation"],
		"context": "Use for bench creation from a deploy candidate.",
	},
	"Deploy Candidate": {
		"filters": ["group", "team", "intel_build", "arm_build"],
		"links": {
			"group": "Release Group",
			"intel_build": "Deploy Candidate Build",
			"arm_build": "Deploy Candidate Build",
		},
		"default_fields": [
			"group",
			"team",
			"intel_build",
			"arm_build",
			"requires_intel_build",
			"requires_arm_build",
		],
		"context": "Use for candidate-to-build mapping in deploy reports.",
	},
	"Deploy Candidate Build": {
		"filters": ["deploy_candidate", "status", "group", "team", "platform"],
		"links": {"deploy_candidate": "Deploy Candidate", "group": "Release Group", "build_server": "Server"},
		"default_fields": [
			"deploy_candidate",
			"status",
			"group",
			"team",
			"platform",
			"build_server",
			"build_duration",
		],
		"context": "Use for image/build failures; steps have command output.",
	},
	"Deploy Candidate Build Step": {
		"filters": ["parent", "status", "stage", "step"],
		"links": {"parent": "Deploy Candidate Build"},
		"default_fields": ["parent", "stage", "step", "status", "cached", "duration"],
		"context": "Use for failed build command/stage details.",
	},
	"Release Group": {
		"filters": ["public", "enabled", "version", "team", "default"],
		"default_fields": ["title", "version", "team", "public", "enabled", "default"],
		"context": "Use for app/version config shared by benches/sites.",
	},
	"Agent Job": {
		"filters": ["status", "site", "server", "bench", "job_type", "reference_doctype", "reference_name"],
		"links": {
			"site": "Site",
			"server": ["Server", "Database Server", "Proxy Server"],
			"bench": "Bench",
			"host": "Site Domain",
			"reference_name": [
				"Site",
				"Site Backup",
				"Site Update",
				"Site Migration",
				"Bench",
				"Server",
				"Database Server",
				"Proxy Server",
			],
		},
		"default_fields": ["job_type", "status", "site", "server", "bench", "reference_name", "duration"],
		"query_examples": [
			{"site": "<site-name>"},
			{"status": "Failure"},
			{"reference_doctype": "<doctype>", "reference_name": "<name>"},
		],
		"context": (
			"Use for operation status; full doc has output/steps. "
			"When the user asks for jobs for a Site, Bench, Server, Database Server, Proxy Server, "
			"Site Update, Site Migration, Site Backup, or another document, call "
			"get_agent_jobs_for_document(doctype, name). That tool first checks Link fields on the "
			"source document that point to Agent Job and contain 'job', then queries Agent Job by "
			"site/bench/server or reference_doctype/reference_name."
		),
	},
	"Agent Job Step": {
		"filters": ["agent_job", "status", "step_name"],
		"links": {"agent_job": "Agent Job"},
		"default_fields": ["agent_job", "step_name", "status", "start", "end", "duration"],
		"context": "Use for failed agent step; full doc has output/traceback.",
	},
	"Press Job": {
		"filters": ["status", "job_type", "server_type", "server", "virtual_machine"],
		"links": {
			"server": ["Server", "Database Server", "Proxy Server"],
			"virtual_machine": "Virtual Machine",
		},
		"default_fields": ["job_type", "status", "server", "virtual_machine", "duration"],
		"context": "Use for internal provisioning/maintenance jobs.",
	},
	"Press Job Step": {
		"filters": ["job", "status", "step_name", "job_type"],
		"links": {"job": "Press Job"},
		"default_fields": ["job", "step_name", "status", "start", "end", "duration"],
		"context": "Use for internal job stage failures and traceback.",
	},
	"Press Workflow": {
		"filters": ["status", "linked_doctype", "linked_docname", "callback_status"],
		"links": {
			"linked_docname": [
				"Press Job",
				"Site Update",
				"Site Migration",
				"Deploy Candidate Build",
				"Physical Backup Restoration",
			],
			"exception": "Press Workflow Object",
		},
		"default_fields": [
			"linked_doctype",
			"linked_docname",
			"status",
			"main_method_title",
			"callback_status",
			"duration",
		],
		"query_examples": [
			{"linked_doctype": "<doctype>", "linked_docname": "<name>"},
			{"status": "Failure"},
		],
		"context": "Use for workflow status, callback state, and linked document.",
	},
	"Press Workflow Task": {
		"filters": ["workflow", "parent_task", "status", "method_name"],
		"links": {
			"workflow": "Press Workflow",
			"parent_task": "Press Workflow Task",
			"exception": "Press Workflow Object",
		},
		"default_fields": ["workflow", "parent_task", "method_title", "status", "queue", "duration"],
		"context": "Use for failed workflow task; full doc has stdout/traceback.",
	},
	"Press Workflow Step": {
		"filters": ["parent", "status", "step_method", "task"],
		"links": {"parent": "Press Workflow", "task": "Press Workflow Task"},
		"default_fields": ["parent", "step_title", "status", "step_method", "task"],
		"context": "Use for workflow stage timeline and linked task.",
	},
	"Press Workflow Object": {
		"filters": ["type_qualname", "serialization_failed", "deleted"],
		"default_fields": ["summary", "type_qualname", "serialization_failed", "deleted"],
		"context": "Use when workflow/task exception or output points here.",
	},
	"Incident": {
		"filters": ["status", "type", "server", "cluster", "resource_type", "resource"],
		"links": {
			"server": "Server",
			"cluster": "Cluster",
			"alert": "Prometheus Alert Rule",
			"resource": [
				"Site",
				"Server",
				"Database Server",
				"Proxy Server",
				"Bench",
				"Cluster",
				"Virtual Machine",
			],
		},
		"default_fields": ["status", "type", "server", "cluster", "resource", "subject"],
		"query_examples": [{"server": "<server-name>"}, {"status": "Investigating"}],
		"context": "Use for alert state, affected resource, and timeline.",
	},
	"Alertmanager Webhook Log": {
		"filters": ["status", "alert", "severity", "group_key"],
		"default_fields": ["status", "alert", "severity", "group_key", "external_url"],
		"context": "Use to map raw alerts to incident/report timeline.",
	},
	"Prometheus Alert Rule": {
		"filters": ["enabled", "severity", "silent", "press_job_type"],
		"default_fields": ["severity", "enabled", "silent", "description", "press_job_type"],
		"context": "Use for alert meaning, routing, and reaction jobs.",
	},
	"Silenced Alert": {
		"filters": ["status", "instance_type", "instance", "silence_id"],
		"default_fields": ["status", "instance_type", "instance", "from_time", "to_time", "total_alerts"],
		"context": "Use to explain missing/noisy alerts during incidents.",
	},
	"Error Log": {
		"filters": ["method"],
		"default_fields": ["method", "creation", "modified"],
		"context": "Use after narrowing by method or time; full doc has traceback.",
	},
	"Server Activity": {
		"filters": ["document_type", "document_name", "action", "team"],
		"links": {"document_name": ["Server", "Database Server", "Proxy Server"]},
		"default_fields": ["document_type", "document_name", "action", "reason", "team", "creation"],
		"context": "Use for human-readable server timeline and reasons.",
	},
	"Virtual Machine": {
		"filters": ["status", "cluster", "team", "cloud_provider", "series", "region"],
		"default_fields": ["status", "cluster", "team", "cloud_provider", "region", "series"],
		"context": "Use for cloud instance/provider details behind servers.",
	},
	"Virtual Machine Image": {
		"filters": ["status", "public", "cluster", "region", "series", "platform"],
		"default_fields": ["status", "virtual_machine", "cluster", "region", "series", "public"],
		"context": "Use for VM provisioning image by region/series/platform.",
	},
	"Physical Backup Restoration": {
		"filters": ["site", "status", "site_backup", "destination_server", "job"],
		"links": {
			"site": "Site",
			"site_backup": "Site Backup",
			"destination_server": "Database Server",
			"job": "Agent Job",
		},
		"default_fields": ["site", "status", "site_backup", "destination_server", "job", "duration"],
		"context": "Use for physical restore timeline and destination server.",
	},
	"Physical Backup Restoration Step": {
		"filters": ["parent", "status", "step"],
		"links": {"parent": "Physical Backup Restoration"},
		"default_fields": ["parent", "step", "status", "start", "end", "duration"],
		"context": "Use for failed physical restore stage details.",
	},
}


ALLOWED_DOCTYPES = set(DOCTYPES.keys())
DOCTYPE_SLUGS = {_doctype.lower().replace(" ", "-"): _doctype for _doctype in ALLOWED_DOCTYPES}

BASE_DEFAULT_FIELDS = ["name", "modified"]
BASE_FILTER_FIELDS = {"name", "creation", "modified"}

MAX_LIMIT = 50
MAX_DAYS = 90
SUMMARY_MAX_CHARS = 2000

ALLOWED_ORDER_BY = {
	"modified desc",
	"modified asc",
	"creation desc",
	"creation asc",
}

LARGE_FIELD_NAMES = {
	"data",
	"error",
	"logs",
	"output",
	"payload",
	"response",
	"stderr",
	"stdout",
	"traceback",
}

# Dynamic Link fields need an extra type field to avoid matching the wrong record.
DYNAMIC_LINK_TYPE_FIELDS = {
	"reference_name": "reference_doctype",
	"linked_docname": "linked_doctype",
	"document_name": "document_type",
	"resource": "resource_type",
}

DEBUG_GUIDE = [
	{
		"user_problem": "site issue, app error, update failure, migration failure, backup issue",
		"start_with": "Site",
		"then_check": [
			"Agent Job",
			"Site Activity",
			"Site Action",
			"Site Update",
			"Site Migration",
			"Site Backup",
		],
	},
	{
		"user_problem": "failed job or operation",
		"start_with": "Agent Job",
		"then_check": ["Agent Job Step", "Site", "Bench", "Server"],
	},
	{
		"user_problem": "incident, alert, outage, degraded service",
		"start_with": "Incident",
		"then_check": ["Prometheus Alert Rule", "Server", "Cluster", "Silenced Alert", "Server Activity"],
	},
	{
		"user_problem": "server, provisioning, VM, SSH, Ansible, maintenance issue",
		"start_with": "Server",
		"then_check": [
			"Press Job",
			"Press Job Step",
			"Ansible Play",
			"Ansible Task",
			"Server Activity",
			"Virtual Machine",
		],
	},
	{
		"user_problem": "deploy, build, image build, release issue",
		"start_with": "Deploy Candidate Build",
		"then_check": ["Deploy Candidate Build Step", "Deploy Candidate", "Deploy", "Release Group", "Bench"],
	},
]


@press_mcp.tool()
@system_manager_only
def get_debug_guide() -> list[dict]:
	"""Start here when the user describes a problem but the right doctype is unclear.

	Returns simple routing hints for common support and incident-debugging tasks.
	After choosing a doctype from this guide, call get_doctype(doctype), then query.
	"""
	return DEBUG_GUIDE


@press_mcp.tool()
@system_manager_only
def list_doctypes() -> list[dict]:
	"""List available operational doctypes for discovery only.

	Use this only to choose a doctype. It intentionally returns only a name and a
	short purpose. It does not return filters, fields, links, or examples.

	Next step: call get_doctype(doctype) for the chosen doctype before querying.
	"""
	return [
		{
			"doctype": doctype,
			"purpose": config.get("context"),
		}
		for doctype, config in DOCTYPES.items()
	]


@press_mcp.tool()
@system_manager_only
def get_doctype(doctype: str) -> dict:
	"""Get the query schema for one doctype.

	Call this before list_documents() or get_linked_documents(). It tells you:
	- which filters are allowed
	- which fields are returned by default
	- which doctypes are linked
	- useful query examples, if any
	"""
	doctype = _validate_doctype(doctype)
	return DOCTYPES[doctype]


@press_mcp.tool()
@system_manager_only
def list_documents(
	doctype: str,
	filters: dict | None = None,
	limit: int = 20,
	order_by: str = "modified desc",
	cursor: str | None = None,
) -> dict:
	"""List recent documents for one doctype.

	Call get_doctype(doctype) first if you do not know the allowed filters.
	Returns compact default fields only. Use next_cursor for the next page.
	Use get_document_summary() for more detail.
	"""
	doctype = _validate_doctype(doctype)
	_validate_filters(doctype, filters)
	_validate_order_by(order_by)

	limit = _clamp_limit(limit)
	if limit == 0:
		return redact(_document_list_response(doctype, [], limit, None, order_by, filters))

	offset = _cursor_offset(cursor)
	rows = frappe.get_all(
		doctype,
		filters=filters or {},
		fields=_get_default_fields(doctype),
		order_by=order_by,
		limit=limit + 1,
		start=offset,
	)
	items = rows[:limit]
	next_cursor = str(offset + limit) if len(rows) > limit else None
	return redact(_document_list_response(doctype, items, limit, next_cursor, order_by, filters))


@press_mcp.tool()
@system_manager_only
def get_document(doctype: str, name: str) -> dict:
	"""Fetch one document with compact default fields only.

	Use this for quick inspection. Use get_document_summary() when you need logs,
	tracebacks, child tables, or other detailed fields.
	"""
	doctype = _validate_doctype(doctype)
	_document_exists(doctype, name)

	return redact(
		frappe.db.get_value(
			doctype,
			name,
			_get_default_fields(doctype),
			as_dict=True,
		)
	)


@press_mcp.tool()
@system_manager_only
def get_document_summary(doctype: str, name: str) -> dict:
	"""Fetch compact document fields and point out available large fields.

	Use get_document_field() for logs, tracebacks, child tables or payloads.
	"""
	doctype = _validate_doctype(doctype)
	_document_exists(doctype, name)

	meta = frappe.get_meta(doctype)
	fields = _get_summary_fields(doctype)
	values = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	return redact(
		{
			"doctype": doctype,
			"name": name,
			"fields": {key: _trim_large_values(key, value) for key, value in values.items()},
			"large_fields": _large_fields(meta),
			"child_tables": _child_tables(meta),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_document_field(doctype: str, name: str, fieldname: str, max_chars: int = SUMMARY_MAX_CHARS) -> dict:
	"""Fetch one field from a document.

	Use this for large logs, tracebacks, child tables, payloads or command output.
	"""
	doctype = _validate_doctype(doctype)
	_document_exists(doctype, name)
	if fieldname not in FRAPPE_DEFAULT_FIELDS and not frappe.get_meta(doctype).has_field(fieldname):
		frappe.throw(f"Field '{fieldname}' does not exist for {doctype}")

	max_chars = max(100, min(int(max_chars or SUMMARY_MAX_CHARS), 20000))
	value = frappe.get_doc(doctype, name).as_dict().get(fieldname)
	return redact(
		{
			"doctype": doctype,
			"name": name,
			"fieldname": fieldname,
			"value": _trim_large_values(fieldname, value, max_chars=max_chars),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_full_document(doctype: str, name: str, include_child_tables: bool = False) -> dict:
	"""Fetch one raw full document. Prefer get_document_field for drilldown."""
	doctype = _validate_doctype(doctype)
	_document_exists(doctype, name)

	doc = frappe.get_doc(doctype, name).as_dict()
	if not include_child_tables:
		meta = frappe.get_meta(doctype)
		for fieldname in _child_tables(meta):
			doc.pop(fieldname, None)

	return redact(doc)


@press_mcp.tool()
@system_manager_only
def get_linked_documents(
	doctype: str,
	name: str,
	linked_doctype: str,
	limit: int = 20,
	order_by: str = "modified desc",
) -> list[dict]:
	"""List documents that link to another document.

	Example: from a Site, get linked Agent Job records.
	Call get_doctype(linked_doctype) first if you are unsure what it contains.
	"""
	doctype = _validate_doctype(doctype)
	linked_doctype = _validate_doctype(linked_doctype)
	_validate_order_by(order_by)
	_document_exists(doctype, name)

	link_fields = _get_link_fields(doctype, linked_doctype)
	if not link_fields:
		frappe.throw(f"{linked_doctype} does not link to {doctype}")

	results: list[dict] = []
	seen: set[Any] = set()
	limit = _clamp_limit(limit)
	if limit == 0:
		return []

	for link_field in link_fields:
		if len(results) >= limit:
			break

		linked_docs = list_documents(
			linked_doctype,
			filters=_get_link_filters(doctype, name, linked_doctype, link_field),
			limit=limit - len(results),
			order_by=order_by,
		)["items"]

		for doc in linked_docs:
			doc_name = doc.get("name")
			if doc_name in seen:
				continue

			doc["_link_field"] = link_field
			results.append(doc)
			seen.add(doc_name)

	return results


@press_mcp.tool()
@system_manager_only
def get_agent_jobs_for_document(
	doctype: str,
	name: str,
	limit: int = 20,
	order_by: str = "modified desc",
) -> list[dict]:
	"""Find Agent Jobs for any document.

	Use this instead of get_linked_documents() when looking for Agent Job records.

	Lookup order:
	1. Check Link fields on the source document that point to Agent Job and contain "job",
		like update_job, recover_job, step_job, or job.
	2. Query Agent Job directly:
		- Site uses site
		- Bench uses bench
		- Server, Database Server, and Proxy Server use server
		- All other doctypes use reference_doctype and reference_name
	"""
	doctype = _validate_doctype(doctype)
	_validate_order_by(order_by)
	_document_exists(doctype, name)

	results: list[dict] = []
	seen: set[Any] = set()
	limit = _clamp_limit(limit)
	if limit == 0:
		return []

	for job in _jobs_from_job_fields(doctype, name, limit):
		job_name = job.get("name")
		if job_name in seen:
			continue

		job["_link_strategy"] = "source_job_field"
		results.append(job)
		seen.add(job_name)

		if len(results) >= limit:
			return results

	for job in _jobs_from_agent_job_fields(doctype, name, limit - len(results), order_by):
		job_name = job.get("name")
		if job_name in seen:
			continue

		results.append(job)
		seen.add(job_name)

	return results


@press_mcp.tool()
@system_manager_only
def get_document_versions(doctype: str, name: str, days: int = 7) -> list[dict]:
	"""Get recent change history for one document.

	Default is 7 days. Maximum is 90 days.
	"""
	doctype = _validate_doctype(doctype)
	_document_exists(doctype, name)
	days = _clamp_days(days)

	return redact(
		frappe.get_all(
			"Version",
			filters={
				"ref_doctype": doctype,
				"docname": name,
				"creation": (">=", frappe.utils.add_to_date(days=-days)),
			},
			fields=["creation", "owner", "data"],
			order_by="creation desc",
			limit=20,
		)
	)


def _clamp_limit(limit: int | None) -> int:
	try:
		limit = 20 if limit is None else int(limit)
	except Exception:
		limit = 20

	return max(0, min(limit, MAX_LIMIT))


def _clamp_days(days: int | None) -> int:
	try:
		days = 7 if days is None else int(days)
	except Exception:
		days = 7

	return max(1, min(days, MAX_DAYS))


def _cursor_offset(cursor: str | None) -> int:
	if not cursor:
		return 0
	try:
		return max(0, int(cursor))
	except Exception:
		frappe.throw("cursor must be the next_cursor returned by list_documents")
		return 0


def _document_list_response(
	doctype: str,
	items: list[dict],
	limit: int,
	next_cursor: str | None,
	order_by: str,
	filters: dict | None,
) -> dict:
	return {
		"source": "frappe",
		"doctype": doctype,
		"filters": filters or {},
		"order_by": order_by,
		"items": items,
		"returned": len(items),
		"limit_applied": limit,
		"has_more": bool(next_cursor),
		"next_cursor": next_cursor,
	}


def _validate_doctype(doctype: str) -> str:
	doctype = _normalize_doctype(doctype)
	if doctype not in ALLOWED_DOCTYPES:
		frappe.throw(f"Doctype '{doctype}' is not available through MCP")
	return doctype


def _normalize_doctype(doctype: str) -> str:
	if doctype in ALLOWED_DOCTYPES:
		return doctype

	return DOCTYPE_SLUGS.get(str(doctype or "").strip().lower(), doctype)


def _validate_order_by(order_by: str) -> None:
	if order_by not in ALLOWED_ORDER_BY:
		frappe.throw(f"Order by '{order_by}' is not allowed")


def _validate_filters(doctype: str, filters: dict | None) -> None:
	if not filters:
		return

	allowed_filters = set(DOCTYPES[doctype].get("filters", [])) | BASE_FILTER_FIELDS
	meta = frappe.get_meta(doctype)

	for fieldname in filters:
		if fieldname not in allowed_filters:
			frappe.throw(
				f"Filter '{fieldname}' is not allowed for {doctype}. "
				f"Call get_doctype('{doctype}') to see allowed filters."
			)

		if fieldname not in FRAPPE_DEFAULT_FIELDS and not meta.has_field(fieldname):
			frappe.throw(f"Filter field '{fieldname}' does not exist for {doctype}")


def _get_default_fields(doctype: str) -> list[str]:
	meta = frappe.get_meta(doctype)
	fields = [*BASE_DEFAULT_FIELDS, *DOCTYPES[doctype].get("default_fields", [])]

	return list(
		dict.fromkeys(
			fieldname
			for fieldname in fields
			if fieldname in FRAPPE_DEFAULT_FIELDS or meta.has_field(fieldname)
		)
	)


def _get_summary_fields(doctype: str) -> list[str]:
	meta = frappe.get_meta(doctype)
	fields = [*BASE_DEFAULT_FIELDS, *DOCTYPES[doctype].get("default_fields", [])]
	for field in meta.fields:
		if field.fieldtype in {"Table", "Table MultiSelect"}:
			continue
		if field.fieldtype in {"Code", "HTML Editor", "Long Text", "Markdown Editor", "Text Editor"}:
			continue
		if field.fieldname and field.fieldname.lower() in LARGE_FIELD_NAMES:
			continue
		fields.append(field.fieldname)

	return list(
		dict.fromkeys(
			fieldname
			for fieldname in fields
			if fieldname and (fieldname in FRAPPE_DEFAULT_FIELDS or meta.has_field(fieldname))
		)
	)


def _get_link_fields(source_doctype: str, target_doctype: str) -> list[str]:
	link_fields = []

	for fieldname, link_target in DOCTYPES[target_doctype].get("links", {}).items():
		if link_target == source_doctype or (isinstance(link_target, list) and source_doctype in link_target):
			link_fields.append(fieldname)

	return link_fields


def _get_link_filters(source_doctype: str, source_name: str, target_doctype: str, link_field: str) -> dict:
	filters = {link_field: source_name}
	type_field = DYNAMIC_LINK_TYPE_FIELDS.get(link_field)

	if type_field and frappe.get_meta(target_doctype).has_field(type_field):
		filters[type_field] = source_doctype

	return filters


def _jobs_from_job_fields(doctype: str, name: str, limit: int) -> list[dict]:
	job_fields = _agent_job_link_fields(doctype)
	if not job_fields:
		return []

	doc = frappe.db.get_value(doctype, name, job_fields, as_dict=True) or {}
	jobs: list[dict] = []

	for fieldname in job_fields:
		if len(jobs) >= limit:
			break

		job_name = doc.get(fieldname)
		if not job_name:
			continue

		if frappe.db.exists("Agent Job", job_name):
			job = redact(
				frappe.db.get_value(
					"Agent Job",
					job_name,
					_get_default_fields("Agent Job"),
					as_dict=True,
				)
			)
			if not job:
				continue

			job["_link_field"] = fieldname
			jobs.append(job)

	return jobs


def _agent_job_link_fields(doctype: str) -> list[str]:
	return [
		field.fieldname
		for field in frappe.get_meta(doctype).fields
		if field.fieldname
		and "job" in field.fieldname.lower()
		and field.fieldtype == "Link"
		and field.options == "Agent Job"
	]


def _jobs_from_agent_job_fields(
	doctype: str,
	name: str,
	limit: int,
	order_by: str,
) -> list[dict]:
	if limit <= 0:
		return []

	field_by_doctype = {
		"Site": "site",
		"Bench": "bench",
		"Server": "server",
		"Database Server": "server",
		"Proxy Server": "server",
	}

	if doctype in field_by_doctype:
		link_field = field_by_doctype[doctype]
		filters = {link_field: name}
		strategy = f"agent_job_{link_field}"
	else:
		filters = {
			"reference_doctype": doctype,
			"reference_name": name,
		}
		strategy = "agent_job_reference"

	rows = list_documents(
		"Agent Job",
		filters=filters,
		limit=limit,
		order_by=order_by,
	)["items"]

	for row in rows:
		row["_link_strategy"] = strategy

	return rows


def _trim_large_values(fieldname: str, value, *, max_chars: int = SUMMARY_MAX_CHARS):
	if isinstance(value, str) and fieldname.lower() in LARGE_FIELD_NAMES:
		if len(value) > max_chars:
			return value[:max_chars] + "..."
		return value

	if isinstance(value, dict):
		return {key: _trim_large_values(key, item, max_chars=max_chars) for key, item in value.items()}

	if isinstance(value, list):
		return [_trim_large_values(fieldname, item, max_chars=max_chars) for item in value]

	return value


def _large_fields(meta) -> list[str]:
	large_types = {"Code", "HTML Editor", "Long Text", "Markdown Editor", "Text Editor"}
	return [
		field.fieldname
		for field in meta.fields
		if field.fieldname
		and (field.fieldtype in large_types or field.fieldname.lower() in LARGE_FIELD_NAMES)
	]


def _child_tables(meta) -> list[str]:
	return [
		field.fieldname
		for field in meta.fields
		if field.fieldname and field.fieldtype in {"Table", "Table MultiSelect"}
	]


def _document_exists(doctype: str, name: str) -> None:
	if not frappe.db.exists(doctype, name):
		frappe.throw(f"{doctype} '{name}' not found")
