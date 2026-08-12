from __future__ import annotations

import copy
import json
from typing import Any

import frappe
import requests
from frappe.utils.password import get_decrypted_password

_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024
_TIMEOUT = 60


def analyse(investigation_name: str, payload: dict[str, Any], report: dict[str, Any]) -> str:
	"""Send the redacted payload and deterministic report to Claude and return its analysis."""
	api_key = get_decrypted_password("Press Settings", "Press Settings", "anthropic_api_key")
	prompt = _build_prompt(_anonymise(payload), report)
	return _call_claude(api_key, prompt)


_SITE_IDENTITY_FIELDS = {"name", "bench", "server", "database_server", "cluster", "group"}
_BENCH_IDENTITY_FIELDS = {"name", "server", "database_server", "cluster", "candidate", "build"}


def _anonymise(payload: dict[str, Any]) -> dict[str, Any]:
	"""Strip platform identifiers before the payload leaves the platform."""
	p = copy.deepcopy(payload)
	if isinstance(p.get("site"), dict):
		for field in _SITE_IDENTITY_FIELDS:
			p["site"].pop(field, None)
	if isinstance(p.get("bench"), dict):
		for field in _BENCH_IDENTITY_FIELDS:
			p["bench"].pop(field, None)
	_anonymise_database_processes(p.get("database_processes"))
	_anonymise_tenant_share(p.get("database_slow_query_share"))
	_anonymise_tenant_share(p.get("app_server_request_share"))
	return p


def _anonymise_tenant_share(share: Any) -> None:
	"""The busiest tenant on the database server is named only if it is this site."""
	if isinstance(share, dict) and not share.get("busiest_site_is_target"):
		share["busiest_site"] = None


def _anonymise_database_processes(database_processes: Any) -> None:
	"""Processlist rows name the site behind each connection; other tenants stay unnamed."""
	if not isinstance(database_processes, dict):
		return
	for process in database_processes.get("processes") or []:
		if not process.get("is_target_site"):
			process["site"] = None


def _build_prompt(payload: dict[str, Any], report: dict[str, Any]) -> str:
	evidence = "\n".join(f"  - {e}" for e in (report.get("evidence") or []))
	next_steps = "\n".join(f"  - {s}" for s in (report.get("recommended_next_steps") or []))
	payload_text = json.dumps(payload, indent=2, default=str)

	return f"""You are a support engineer reviewing an automated investigation for a Frappe Cloud site.

Deterministic analysis findings:
  Summary: {report.get("summary", "")}
  Likely cause: {report.get("likely_cause", "")}
  Confidence: {report.get("confidence", "")}
  Evidence:
{evidence}
  Recommended next steps:
{next_steps}

Full redacted investigation payload:
{payload_text}

Review the payload and findings. Respond with:
1. Whether you agree with the likely cause, or a refined diagnosis if you see something different.
2. Any additional signals the deterministic analysis may have missed.
3. Your recommended next steps for the support agent.

Failing agent jobs are almost always a symptom, not the cause — a job fails because the bench
is down, the disk is full, or a deploy went bad. Use them to narrow down when and where to look,
but do not present them as the diagnosis.

Be concise and actionable. Cite only evidence present in the payload. Do not invent information."""


def _call_claude(api_key: str, prompt: str) -> str:
	headers = {
		"x-api-key": api_key,
		"anthropic-version": _ANTHROPIC_VERSION,
		"content-type": "application/json",
	}
	body = {
		"model": _MODEL,
		"max_tokens": _MAX_TOKENS,
		"messages": [{"role": "user", "content": prompt}],
	}

	try:
		response = requests.post(_ANTHROPIC_MESSAGES_URL, json=body, headers=headers, timeout=_TIMEOUT)
		response.raise_for_status()
	except requests.Timeout:
		frappe.throw("Claude API request timed out.")  # nosemgrep: non-actionable-error-message
	except requests.HTTPError:
		frappe.throw(f"Claude API request failed with HTTP {response.status_code}: {response.text[:200]}")
	except requests.RequestException as e:
		frappe.throw(f"Claude API request failed: {type(e).__name__}")

	data = response.json()
	content = data.get("content") or []
	text_blocks = [block["text"] for block in content if block.get("type") == "text"]
	return "\n".join(text_blocks).strip()
