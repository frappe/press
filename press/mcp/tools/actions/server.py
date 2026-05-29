# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import posixpath
import re
import shlex

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.utils import system_manager_only
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.utils import poly_get_doctype

_PROXY_REFUSED = (
	"Proxy server restarts are never allowed via MCP — "
	"they affect all sites on the cluster. Use the dashboard or escalate manually."
)
_MAX_FILE_BYTES = 100 * 1024
_MAX_DIRECTORY_OUTPUT_LINES = 200
_DEFAULT_TAIL_LINES = 100
_MAX_TAIL_LINES = 500
_DEFAULT_SUPERVISOR_TAIL_BYTES = 1000
_MAX_SUPERVISOR_TAIL_BYTES = _MAX_FILE_BYTES
_DEFAULT_GREP_MATCHES = 100
_MAX_GREP_MATCHES = 500
_MAX_GREP_CONTEXT_LINES = 50
_SERVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@:+-]*$")
_SAFE_SYSTEMCTL_COMMANDS = {
	"cat",
	"is-active",
	"is-enabled",
	"list-dependencies",
	"show",
	"status",
}
_MUTATING_SYSTEMCTL_COMMANDS = {
	"reload",
	"restart",
	"start",
	"stop",
	"try-reload-or-restart",
	"try-restart",
}
_SAFE_SUPERVISOR_COMMANDS = {"status"}
_MUTATING_SUPERVISOR_COMMANDS = {"kill", "restart", "start", "stop"}
_SENSITIVE_PATH_PARTS = (
	"/.ssh",
	"/etc/passwd",
	"/etc/shadow",
	"/etc/sudoers",
	"/etc/ssl/private",
	"/secrets/",
	"/tls/",
	"/vault/",
	".htpasswd",
	"authorized_keys",
	"id_rsa",
	"id_dsa",
	"id_ecdsa",
	"id_ed25519",
	"private_key",
)
_SENSITIVE_EXACT_PATHS = {
	"/proc/kcore",
	"/proc/keys",
	"/proc/sysrq-trigger",
}
_SENSITIVE_PATH_PREFIXES = (
	"/sys/firmware",
	"/sys/kernel/debug",
	"/sys/kernel/security",
)


@press_mcp.tool()
@system_manager_only
def list_directory_in_server(server: str, directory: str) -> dict:
	"""List a server directory.

	Returns at most 200 shell output lines. Refuses host-system paths that commonly contain secrets.
	"""
	_validate_server(server)
	directory = _validate_safe_path(directory, path_type="directory")
	quoted_directory = shlex.quote(directory)
	result = _run_checked(
		_directory_guard(quoted_directory)
		+ f"ls -lah --time-style=long-iso -- {quoted_directory} | head -n {_MAX_DIRECTORY_OUTPUT_LINES}",
		server,
		"Failed to list directory",
	)
	return _tool_response(
		{
			"action": "list_directory_in_server",
			"server": server,
			"directory": directory,
			"max_output_lines": _MAX_DIRECTORY_OUTPUT_LINES,
			"note": "Directory output is capped at shell output lines, including the ls total line.",
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def get_file_in_server(server: str, file: str) -> dict:
	"""Read a small text file from a server.

	Output is capped at 100 KiB and redacted before return. Refuses host-system
	paths that commonly contain credentials, private keys or other secrets.
	"""
	_validate_server(server)
	file = _validate_safe_path(file, path_type="file")
	quoted_file = shlex.quote(file)
	result = _run_checked(
		_file_guard(quoted_file)
		+ f"size=$(wc -c < {quoted_file}) && "
		+ f"head -c {_MAX_FILE_BYTES} -- {quoted_file} && "
		+ f'if [ "$size" -gt {_MAX_FILE_BYTES} ]; then '
		+ f"printf '\\n[TRUNCATED: file is %s bytes; returned first {_MAX_FILE_BYTES} bytes]\\n' \"$size\"; "
		+ "fi",
		server,
		"Failed to read file",
	)
	return _tool_response(
		{
			"action": "get_file_in_server",
			"server": server,
			"file": file,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def tail_file_in_server(server: str, file: str, lines: int = _DEFAULT_TAIL_LINES) -> dict:
	"""Return the last lines from a server file without streaming.

	Output is capped by line count and by 100 KiB. Refuses host-system paths that
	commonly contain credentials, private keys or other secrets.
	"""
	_validate_server(server)
	file = _validate_safe_path(file, path_type="file")
	lines = _validate_limit(lines, minimum=1, maximum=_MAX_TAIL_LINES, label="Lines")
	quoted_file = shlex.quote(file)
	result = _run_checked(
		_file_guard(quoted_file) + _capture_command(f"tail -n {lines} -- {quoted_file}"),
		server,
		"Failed to tail file",
	)
	return _tool_response(
		{
			"action": "tail_file_in_server",
			"server": server,
			"file": file,
			"lines": lines,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def grep_file_in_server(
	server: str,
	file: str,
	pattern: str,
	limit: int = _DEFAULT_GREP_MATCHES,
	ignore_case: bool = False,
	before_context: int = 0,
	after_context: int = 0,
) -> dict:
	"""Search a server file with a fixed-string grep.

	Returns at most 500 matching lines. No-match results are returned as
	successful empty output. Refuses host-system paths that commonly contain secrets.
	"""
	_validate_server(server)
	file = _validate_safe_path(file, path_type="file")
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
	result = _run_checked(
		_file_guard(quoted_file) + _capture_command(command, success_exit_codes=(0, 1)),
		server,
		"Failed to grep file",
	)
	return _tool_response(
		{
			"action": "grep_file_in_server",
			"server": server,
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
def run_systemctl_command_in_server(server: str, service: str, command: str, confirm: bool = False) -> dict:
	"""Run a guarded systemctl command for one service.

	Read-only commands run immediately. Mutating commands require confirm=True.
	Unsupported systemctl commands are refused.
	"""
	_validate_server(server)
	command = _validate_service_command(
		command,
		safe_commands=_SAFE_SYSTEMCTL_COMMANDS,
		mutating_commands=_MUTATING_SYSTEMCTL_COMMANDS,
	)
	service = _validate_service_name(service)
	mutating = command in _MUTATING_SYSTEMCTL_COMMANDS

	if mutating and not confirm:
		return {
			"action": "run_systemctl_command_in_server",
			"server": server,
			"service": service,
			"command": command,
			"impact": f"Runs systemctl {command} for {service}. This may affect service availability.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	result = _run_checked(
		f"systemctl {shlex.quote(command)} -- {shlex.quote(service)}",
		server,
		"Failed to run systemctl command",
	)
	return _tool_response(
		{
			"action": "run_systemctl_command_in_server",
			"server": server,
			"service": service,
			"command": command,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def run_supervisor_command_in_server(server: str, service: str, command: str, confirm: bool = False) -> dict:
	"""Run a guarded supervisorctl command for one program or group.

	Status runs immediately. Start, stop and restart require confirm=True.
	Unsupported supervisorctl commands are refused.
	"""
	_validate_server(server)
	command = _validate_service_command(
		command,
		safe_commands=_SAFE_SUPERVISOR_COMMANDS,
		mutating_commands=_MUTATING_SUPERVISOR_COMMANDS,
	)
	service = _validate_service_name(service)
	mutating = command in _MUTATING_SUPERVISOR_COMMANDS

	if mutating and not confirm:
		return {
			"action": "run_supervisor_command_in_server",
			"server": server,
			"service": service,
			"command": command,
			"impact": f"Runs supervisorctl {command} for {service}. This may affect process availability.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	result = _run_checked(
		f"supervisorctl {shlex.quote(command)} {shlex.quote(service)}",
		server,
		"Failed to run supervisorctl command",
	)
	return _tool_response(
		{
			"action": "run_supervisor_command_in_server",
			"server": server,
			"service": service,
			"command": command,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def tail_supervisor_log_in_server(
	server: str,
	service: str,
	stream: str = "stdout",
	bytes: int = _DEFAULT_SUPERVISOR_TAIL_BYTES,
) -> dict:
	"""Return bounded supervisor log output for one program without streaming.

	Uses supervisorctl tail -N without follow mode, so output is byte-bounded
	by supervisorctl itself.
	"""
	_validate_server(server)
	service = _validate_service_name(service)
	stream = _validate_supervisor_stream(stream)
	bytes = _validate_limit(
		bytes,
		minimum=1,
		maximum=_MAX_SUPERVISOR_TAIL_BYTES,
		label="Bytes",
	)
	result = _run_checked(
		_capture_command(f"supervisorctl tail -{bytes} {shlex.quote(service)} {shlex.quote(stream)}"),
		server,
		"Failed to tail supervisor log",
	)
	return _tool_response(
		{
			"action": "tail_supervisor_log_in_server",
			"server": server,
			"service": service,
			"stream": stream,
			"bytes": bytes,
			"max_bytes": _MAX_FILE_BYTES,
		},
		result,
	)


@press_mcp.tool()
@system_manager_only
def reboot_in_server(server: str, confirm: bool = False) -> dict:
	"""Reboot an app or database server.

	For AWS EC2: uses serial console reboot (sysrq) — harder reset that
	recovers hung kernels. For all other providers: normal VM reboot via
	the provider API.

	Proxy servers are never rebooted via this tool.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if frappe.db.exists("Proxy Server", server):
		frappe.throw(_PROXY_REFUSED)

	server_doctype = _validate_server(server)
	server_doc = frappe.get_doc(server_doctype, server)

	provider = server_doc.provider
	is_aws = provider == "AWS EC2"
	method = "serial console reboot (sysrq)" if is_aws else f"VM reboot via {provider}"

	if not confirm:
		return {
			"action": "reboot_in_server",
			"server": server,
			"server_type": server_doctype,
			"provider": provider,
			"method": method,
			"impact": (
				"Hard reboot via serial console. Causes downtime for all benches/sites on this server."
				if is_aws
				else "Normal VM reboot. Causes downtime for all benches/sites on this server."
			),
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	if is_aws:
		server_doc.reboot_with_serial_console()
	else:
		server_doc.reboot()

	return {
		"action": "reboot_in_server",
		"server": server,
		"server_type": server_doctype,
		"provider": provider,
		"method": method,
		"status": "triggered",
	}


def _validate_server(server: str) -> str:
	server_doctype = poly_get_doctype(["Server", "Database Server"], server)
	if not server_doctype or not frappe.db.exists(server_doctype, server):
		frappe.throw(f"Server {server!r} not found")

	return server_doctype


def _validate_safe_path(path: str, path_type: str) -> str:
	if not isinstance(path, str) or not path.strip():
		frappe.throw(f"{path_type.title()} path is required")

	if "\x00" in path or "\n" in path or "\r" in path:
		frappe.throw(f"{path_type.title()} path contains invalid characters")

	raw_path = path.strip()
	if not raw_path.startswith("/"):
		frappe.throw(f"{path_type.title()} path must be absolute")

	if ".." in raw_path.split("/"):
		frappe.throw(f"{path_type.title()} path must not contain parent-directory segments")

	normalized_path = posixpath.normpath(raw_path)
	if normalized_path != raw_path:
		frappe.throw(f"{path_type.title()} path must be a normalized absolute path")

	lower_path = normalized_path.lower()
	if _is_sensitive_path(lower_path):
		frappe.throw(f"Refusing to read sensitive {path_type} path {path!r}")

	return normalized_path


def _is_sensitive_path(lower_path: str) -> bool:
	if any(part in lower_path for part in _SENSITIVE_PATH_PARTS):
		return True

	if lower_path in _SENSITIVE_EXACT_PATHS:
		return True

	if lower_path.startswith(_SENSITIVE_PATH_PREFIXES):
		return True

	path_parts = lower_path.strip("/").split("/")
	return len(path_parts) >= 3 and path_parts[0] == "proc" and path_parts[2] == "environ"


def _validate_service_command(command: str, safe_commands: set[str], mutating_commands: set[str]) -> str:
	if not isinstance(command, str) or not command.strip():
		frappe.throw("Command is required.\nPass one of the allowed systemctl or supervisorctl commands.")

	normalized_command = command.strip().lower()
	allowed_commands = safe_commands | mutating_commands
	if normalized_command not in allowed_commands:
		frappe.throw(
			f"Unsupported command {command!r}. Allowed commands: {', '.join(sorted(allowed_commands))}"
		)

	return normalized_command


def _validate_service_name(service: str) -> str:
	if not isinstance(service, str) or not service.strip():
		frappe.throw(
			"Service is required.\nPass a specific systemd service, supervisor program, or group name."
		)

	service = service.strip()
	if service == "all":
		frappe.throw(
			"Service name 'all' is not allowed.\nPass one specific service or process group instead."
		)

	if not _SERVICE_NAME_PATTERN.match(service):
		frappe.throw(f"Invalid service name {service!r}")

	return service


def _validate_supervisor_stream(stream: str) -> str:
	if not isinstance(stream, str) or not stream.strip():
		frappe.throw("Supervisor stream is required.\nPass stream='stdout' or stream='stderr'.")

	stream = stream.strip().lower()
	if stream not in {"stdout", "stderr"}:
		frappe.throw("Supervisor stream must be stdout or stderr.\nPass one of those two exact values.")

	return stream


def _validate_limit(value: int, minimum: int, maximum: int, label: str) -> int:
	try:
		value = int(value)
	except (TypeError, ValueError):
		frappe.throw(f"{label} must be an integer")

	if value < minimum or value > maximum:
		frappe.throw(f"{label} must be between {minimum} and {maximum}")

	return value


def _validate_grep_pattern(pattern: str) -> str:
	if not isinstance(pattern, str) or not pattern:
		frappe.throw("Grep pattern is required.\nPass a non-empty fixed string to search for.")

	if "\x00" in pattern or "\n" in pattern or "\r" in pattern:
		frappe.throw(
			"Grep pattern contains invalid characters.\nPass a single-line pattern without null bytes."
		)

	return pattern


def _file_guard(quoted_path: str) -> str:
	return (
		f"if [ ! -e {quoted_path} ]; then "
		f"printf 'File not found: %s\\n' {quoted_path} >&2; exit 2; "
		f"fi; "
		f"if [ ! -f {quoted_path} ]; then "
		f"printf 'Path is not a regular file: %s\\n' {quoted_path} >&2; exit 3; "
		f"fi; "
	)


def _directory_guard(quoted_path: str) -> str:
	return (
		f"if [ ! -e {quoted_path} ]; then "
		f"printf 'Directory not found: %s\\n' {quoted_path} >&2; exit 2; "
		f"fi; "
		f"if [ ! -d {quoted_path} ]; then "
		f"printf 'Path is not a directory: %s\\n' {quoted_path} >&2; exit 3; "
		f"fi; "
	)


def _capture_command(command: str, success_exit_codes: tuple[int, ...] = (0,)) -> str:
	success_checks = " || ".join(f'[ "$status" -eq {code} ]' for code in success_exit_codes)
	return (
		f"output=$({command} 2>&1); "
		"status=$?; "
		f"if {success_checks}; then "
		f'printf "%s\\n" "$output" | head -c {_MAX_FILE_BYTES}; '
		"else "
		'printf "%s\\n" "$output" >&2; exit "$status"; '
		"fi"
	)


def _run_command(command: str, server: str) -> dict:
	_validate_server(server)

	result = AnsibleAdHoc(sources=f"{server},").run(command, server, raw_params=True)
	if not result or not isinstance(result, list) or not len(result) > 0:
		frappe.throw("Failed to run the required command.\nCheck that the server is reachable and try again.")

	return result[0]


def _run_checked(command: str, server: str, failure_message: str) -> dict:
	result = _run_command(command, server)
	_throw_failed_command(result, failure_message)
	return result


def _throw_failed_command(result: dict, fallback_message: str) -> None:
	if result.get("status") == "Success":
		return

	message = result.get("error") or result.get("exception") or fallback_message
	frappe.throw(redact(message))


def _tool_response(data: dict, result: dict) -> dict:
	result = redact(result)
	return {
		**data,
		"status": result.get("status"),
		"output": result.get("output"),
		"error": result.get("error"),
		"exit_code": result.get("exit_code"),
		"result": result,
	}
