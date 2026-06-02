# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import shlex

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.tools.actions.server import (
	_DEFAULT_GREP_MATCHES,
	_DEFAULT_SUPERVISOR_TAIL_BYTES,
	_DEFAULT_TAIL_LINES,
	_MAX_DIRECTORY_OUTPUT_LINES,
	_MAX_FILE_BYTES,
	_MAX_GREP_CONTEXT_LINES,
	_MAX_GREP_MATCHES,
	_MAX_SUPERVISOR_TAIL_BYTES,
	_MAX_TAIL_LINES,
	_MUTATING_SUPERVISOR_COMMANDS,
	_SAFE_SUPERVISOR_COMMANDS,
	_capture_command,
	_directory_guard,
	_file_guard,
	_throw_failed_command,
	_tool_response,
	_validate_grep_pattern,
	_validate_limit,
	_validate_safe_path,
	_validate_service_command,
	_validate_service_name,
	_validate_supervisor_stream,
)
from press.mcp.utils import system_manager_only
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

_CANCEL_STUCK_JOBS_LIMIT = 50


@press_mcp.tool()
@system_manager_only
def restart_bench(bench: str, confirm: bool = False) -> dict:
	"""Restart gunicorn and workers for a bench.

	Causes brief downtime (seconds) while processes restart. All sites on
	the bench are affected. Common fix for hung workers or memory leaks.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	if not confirm:
		bench_doc = frappe.get_doc("Bench", bench)
		site_count = frappe.db.count("Site", {"bench": bench, "status": "Active"})
		return {
			"action": "restart_bench",
			"bench": bench,
			"group": bench_doc.group,
			"active_sites_affected": site_count,
			"impact": "Restarts gunicorn and workers. Brief downtime for all sites on this bench.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	frappe.get_doc("Bench", bench).restart()
	return {"action": "restart_bench", "bench": bench, "status": "triggered"}


@press_mcp.tool()
@system_manager_only
def cancel_stuck_jobs(bench: str, confirm: bool = False) -> dict:
	"""Cancel agent jobs stuck in Running state on a bench.

	Targets jobs that are Running on this bench and are typically safe
	to cancel: Backup Site, Restore Site, Fetch Database Table Schema.
	These commonly get stuck during a database reboot or upgrade.

	For broader incident-level job management (all job types, incident
	scope), use the Incident document's cancel_stuck_jobs action directly.

	Pass confirm=True to execute. Without it, lists jobs that would be cancelled.
	"""
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	cancellable_job_types = [
		"Backup Site",
		"Restore Site",
		"Fetch Database Table Schema",
	]

	stuck_jobs = frappe.get_all(
		"Agent Job",
		filters={
			"bench": bench,
			"status": "Running",
			"job_type": ("in", cancellable_job_types),
		},
		fields=["name", "job_type", "site", "creation"],
		order_by="creation asc",
		limit=_CANCEL_STUCK_JOBS_LIMIT,
	)

	if not stuck_jobs:
		return {
			"action": "cancel_stuck_jobs",
			"bench": bench,
			"stuck_jobs": [],
			"note": "No stuck jobs found.",
		}

	if not confirm:
		return {
			"action": "cancel_stuck_jobs",
			"bench": bench,
			"stuck_jobs": stuck_jobs,
			"impact": f"Will cancel up to {_CANCEL_STUCK_JOBS_LIMIT} stuck job(s) in this request.",
			"limit": _CANCEL_STUCK_JOBS_LIMIT,
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	cancelled = []
	for job in stuck_jobs:
		frappe.get_doc("Agent Job", job.name).cancel_job()
		cancelled.append({"name": job.name, "job_type": job.job_type, "site": job.site})

	return {
		"action": "cancel_stuck_jobs",
		"bench": bench,
		"cancelled": cancelled,
		"limit": _CANCEL_STUCK_JOBS_LIMIT,
		"status": "triggered",
	}


@press_mcp.tool()
@system_manager_only
def list_directory_in_bench(bench: str, directory: str) -> dict:
	"""List a directory inside a bench container.

	Returns at most 200 shell output lines. Refuses paths that commonly contain secrets.
	"""
	bench_doc = _validate_bench(bench)
	directory = _validate_safe_bench_path(directory, path_type="directory")
	quoted_directory = shlex.quote(directory)
	result = _run_checked_in_bench(
		_directory_guard(quoted_directory)
		+ f"ls -lah --time-style=long-iso -- {quoted_directory} | head -n {_MAX_DIRECTORY_OUTPUT_LINES}",
		bench_doc,
		"Failed to list bench directory",
	)
	return _tool_response(
		{
			"action": "list_directory_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"directory": directory,
			"max_output_lines": _MAX_DIRECTORY_OUTPUT_LINES,
			"note": "Directory output is capped at shell output lines, including the ls total line.",
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def get_file_in_bench(bench: str, file: str) -> dict:
	"""Read a small text file from inside a bench container.

	The bench folder inside the container is /home/frappe/frappe-bench.
	Output includes ls -alh metadata, then file content capped at 100 KiB and
	redacted before return. Refuses paths that commonly contain credentials,
	private keys or other secrets.
	"""
	bench_doc = _validate_bench(bench)
	file = _validate_safe_bench_path(file, path_type="file")
	quoted_file = shlex.quote(file)
	result = _run_checked_in_bench(
		_file_guard(quoted_file)
		+ f"ls -alh --time-style=long-iso -- {quoted_file} && "
		+ "printf '\\n--- file content ---\\n' && "
		+ f"size=$(wc -c < {quoted_file}) && "
		+ f"head -c {_MAX_FILE_BYTES} -- {quoted_file} && "
		+ f'if [ "$size" -gt {_MAX_FILE_BYTES} ]; then '
		+ f"printf '\\n[TRUNCATED: file is %s bytes; returned first {_MAX_FILE_BYTES} bytes]\\n' \"$size\"; "
		+ "fi",
		bench_doc,
		"Failed to read bench file",
	)
	return _tool_response(
		{
			"action": "get_file_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"file": file,
			"bench_folder": "/home/frappe/frappe-bench",
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def get_disk_usage_in_bench(bench: str, path: str) -> dict:
	"""Return du -sh for a path inside a bench container.

	Use this to quickly estimate file or directory size. Refuses paths that
	commonly contain credentials, private keys or other secrets.
	"""
	bench_doc = _validate_bench(bench)
	path = _validate_safe_bench_path(path, path_type="path")
	quoted_path = shlex.quote(path)
	result = _run_checked_in_bench(
		f"if [ ! -e {quoted_path} ]; then "
		f"printf 'Path not found: %s\\n' {quoted_path} >&2; exit 2; "
		f"fi; du -sh -- {quoted_path}",
		bench_doc,
		"Failed to get bench disk usage",
	)
	return _tool_response(
		{
			"action": "get_disk_usage_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"path": path,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def tail_file_in_bench(bench: str, file: str, lines: int = _DEFAULT_TAIL_LINES) -> dict:
	"""Return the last lines from a bench-container file without streaming.

	Output is capped by line count and by 100 KiB. Refuses paths that commonly
	contain credentials, private keys or other secrets.
	"""
	bench_doc = _validate_bench(bench)
	file = _validate_safe_bench_path(file, path_type="file")
	lines = _validate_limit(lines, minimum=1, maximum=_MAX_TAIL_LINES, label="Lines")
	quoted_file = shlex.quote(file)
	result = _run_checked_in_bench(
		_file_guard(quoted_file) + _capture_command(f"tail -n {lines} -- {quoted_file}"),
		bench_doc,
		"Failed to tail bench file",
	)
	return _tool_response(
		{
			"action": "tail_file_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"file": file,
			"lines": lines,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def grep_file_in_bench(
	bench: str,
	file: str,
	pattern: str,
	limit: int = _DEFAULT_GREP_MATCHES,
	ignore_case: bool = False,
	before_context: int = 0,
	after_context: int = 0,
) -> dict:
	"""Search a bench-container file with a fixed-string grep.

	Returns at most 500 matching lines. No-match results are returned as
	successful empty output. Refuses paths that commonly contain secrets.
	"""
	bench_doc = _validate_bench(bench)
	file = _validate_safe_bench_path(file, path_type="file")
	pattern = _validate_grep_pattern(pattern)
	limit = _validate_limit(limit, minimum=1, maximum=_MAX_GREP_MATCHES, label="Limit")
	before_context = _validate_limit(
		before_context, minimum=0, maximum=_MAX_GREP_CONTEXT_LINES, label="Before context"
	)
	after_context = _validate_limit(
		after_context, minimum=0, maximum=_MAX_GREP_CONTEXT_LINES, label="After context"
	)
	quoted_file = shlex.quote(file)
	grep_flags = "-n -I -F"
	if ignore_case:
		grep_flags += " -i"
	if before_context:
		grep_flags += f" -B {before_context}"
	if after_context:
		grep_flags += f" -A {after_context}"

	command = f"grep {grep_flags} -m {limit} -- {shlex.quote(pattern)} {quoted_file}"
	result = _run_checked_in_bench(
		_file_guard(quoted_file) + _capture_command(command, success_exit_codes=(0, 1)),
		bench_doc,
		"Failed to grep bench file",
	)
	return _tool_response(
		{
			"action": "grep_file_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"file": file,
			"pattern": pattern,
			"limit": limit,
			"ignore_case": ignore_case,
			"before_context": before_context,
			"after_context": after_context,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def run_supervisor_command_in_bench(bench: str, service: str, command: str, confirm: bool = False) -> dict:
	"""Run a guarded supervisorctl command inside a bench container.

	Status runs immediately. Start, stop and restart require confirm=True.
	Unsupported supervisorctl commands are refused. systemctl is intentionally
	not exposed for bench containers.
	"""
	bench_doc = _validate_bench(bench)
	command = _validate_service_command(
		command,
		safe_commands=_SAFE_SUPERVISOR_COMMANDS,
		mutating_commands=_MUTATING_SUPERVISOR_COMMANDS,
	)
	service = _validate_service_name(service)
	mutating = command in _MUTATING_SUPERVISOR_COMMANDS

	if mutating and not confirm:
		return {
			"action": "run_supervisor_command_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"service": service,
			"command": command,
			"impact": f"Runs supervisorctl {command} for {service}. This may affect bench process availability.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	result = _run_checked_in_bench(
		f"supervisorctl {shlex.quote(command)} {shlex.quote(service)}",
		bench_doc,
		"Failed to run supervisorctl command in bench",
	)
	return _tool_response(
		{
			"action": "run_supervisor_command_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"service": service,
			"command": command,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def tail_supervisor_log_in_bench(
	bench: str,
	service: str,
	stream: str = "stdout",
	bytes: int = _DEFAULT_SUPERVISOR_TAIL_BYTES,
) -> dict:
	"""Return bounded supervisor log output for one bench program without streaming.

	Uses supervisorctl tail -N without follow mode, so output is byte-bounded
	by supervisorctl itself.
	"""
	bench_doc = _validate_bench(bench)
	service = _validate_service_name(service)
	stream = _validate_supervisor_stream(stream)
	bytes = _validate_limit(
		bytes,
		minimum=1,
		maximum=_MAX_SUPERVISOR_TAIL_BYTES,
		label="Bytes",
	)
	result = _run_checked_in_bench(
		_capture_command(f"supervisorctl tail -{bytes} {shlex.quote(service)} {shlex.quote(stream)}"),
		bench_doc,
		"Failed to tail supervisor log in bench",
	)
	return _tool_response(
		{
			"action": "tail_supervisor_log_in_bench",
			"bench": bench_doc.name,
			"server": bench_doc.server,
			"service": service,
			"stream": stream,
			"bytes": bytes,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


def _validate_bench(bench: str):
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	bench_doc = frappe.get_doc("Bench", bench)
	if bench_doc.status not in ["Active", "Broken"]:
		frappe.throw(
			f"Bench {bench_doc.name!r} has status {bench_doc.status}; commands can only run on Active or Broken benches"
		)
	if not bench_doc.server:
		frappe.throw(f"Bench {bench_doc.name!r} does not have a server")

	return bench_doc


def _validate_safe_bench_path(path: str, path_type: str) -> str:
	path = _validate_safe_path(path, path_type)
	if path == "/proc" or path.startswith("/proc/") or path == "/sys" or path.startswith("/sys/"):
		frappe.throw(
			f"Refusing to read {path_type} path {path!r} inside bench container. Use server tools for host diagnostics."
		)

	return path


def _run_in_bench(command: str, bench_doc) -> dict:
	container_command = f"docker exec {shlex.quote(bench_doc.name)} sh -lc {shlex.quote(command)}"
	result = AnsibleAdHoc(sources=f"{bench_doc.server},").run(
		container_command,
		bench_doc.server,
		raw_params=True,
	)
	if not result or not isinstance(result, list) or not len(result) > 0:
		frappe.throw("Failed to run the required command.\nCheck that the server is reachable and try again.")

	return result[0]


def _run_checked_in_bench(command: str, bench_doc, failure_message: str) -> dict:
	result = _run_in_bench(command, bench_doc)
	try:
		_throw_failed_command(result, failure_message)
	except Exception:
		if result.get("error") or result.get("exception"):
			raise
		message = result.get("traceback") or failure_message
		frappe.throw(redact(message))
	return result
