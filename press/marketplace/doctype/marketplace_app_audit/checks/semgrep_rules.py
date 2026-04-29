import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import frappe

from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult

RULES_DIR = Path(__file__).with_name("semgrep-rules")
EXPECTED_CATEGORIES = ("Correctness", "Security")
DEFAULT_CATEGORY = "Security"
DEFAULT_SEVERITY = "Major"
SEMGREP_TO_AUDIT_SEVERITY = {
	"CRITICAL": "Critical",
	"ERROR": "Critical",
	"HIGH": "Major",
	"WARNING": "Minor",
	"MEDIUM": "Minor",
	"LOW": "Info",
	"INFO": "Info",
}
SEVERITY_ORDER = {"Critical": 4, "Major": 3, "Minor": 2, "Info": 1}


def _semgrep_argv_prefix() -> list[str] | None:
	"""
	How to invoke semgrep: prefer bench env (Marketplace Settings audit_bench_path), else PATH.
	Returns argv prefix only, e.g. ["/path/to/semgrep"] or ["/path/to/python", "-m", "semgrep"].
	"""
	bench = (frappe.db.get_single_value("Marketplace Settings", "audit_bench_path") or "").strip()
	if bench:
		semgrep_bin = os.path.join(bench, "env", "bin", "semgrep")
		python_bin = os.path.join(bench, "env", "bin", "python")
		if os.path.isfile(semgrep_bin) and os.access(semgrep_bin, os.X_OK):
			return [semgrep_bin]
		if os.path.isfile(python_bin) and os.access(python_bin, os.X_OK):
			return [python_bin, "-m", "semgrep"]

	which = shutil.which("semgrep")
	if which:
		return [which]
	return None


def run_semgrep_rules(clone_dir: str) -> list[CheckResult]:
	if not RULES_DIR.exists():
		return [
			CheckResult(
				check_id="semgrep_rules_missing",
				check_name="Semgrep Rules Directory",
				category=DEFAULT_CATEGORY,
				severity="Info",
				result="Error",
				message="Semgrep rules directory is missing.",
				details=json.dumps({"rules_dir": str(RULES_DIR)}),
				remediation="Create the semgrep-rules directory and add rule files.",
			)
		]

	prefix = _semgrep_argv_prefix()
	if prefix is None:
		return [
			CheckResult(
				check_id="semgrep_unavailable",
				check_name="Semgrep Binary Available",
				category=DEFAULT_CATEGORY,
				severity="Info",
				result="Error",
				message="Semgrep is not available (no bench env binary and not on PATH).",
				details=json.dumps({"rules_dir": str(RULES_DIR)}),
				remediation=(
					"Set Marketplace Settings → Marketplace audit bench path to a bench with "
					"`env/bin/semgrep` or `pip install semgrep` in that env, or install semgrep on PATH."
				),
			)
		]

	# scan flag: This is the recommended command for scanning local codebases or scanning a project when we don't have a Semgrep account.
	# It is also recommended for writing and testing custom rules.
	# quiet flag: only print findings and suppress other informational messages
	# --config flag: path to the Semgrep ruleset
	# --json flag: output results in JSON format
	# .: path to the codebase to scan
	# scan: local rules; quiet: findings only; json: machine-readable output; cwd: cloned app
	cmd = [
		*prefix,
		"scan",
		"--config",
		str(RULES_DIR.resolve()),
		"--json",
		"--quiet",
		".",
	]
	completed = subprocess.run(
		cmd,
		cwd=clone_dir,
		capture_output=True,
		text=True,
		check=False,
	)

	# Semgrep returns 1 when findings are present.
	if completed.returncode not in (0, 1):
		return [
			CheckResult(
				check_id="semgrep_command_failed",
				check_name="Semgrep Scan",
				category=DEFAULT_CATEGORY,
				severity="Info",
				result="Error",
				message="Semgrep failed before returning scan results.",
				details=json.dumps(
					{
						"returncode": completed.returncode,
						"stdout": completed.stdout.strip(),
						"stderr": completed.stderr.strip(),
					}
				),
				remediation="Fix the semgrep installation, rule syntax, or scan invocation.",
			)
		]

	try:
		payload = json.loads(completed.stdout or "{}")
	except json.JSONDecodeError:
		return [
			CheckResult(
				check_id="semgrep_invalid_json",
				check_name="Semgrep JSON Output",
				category=DEFAULT_CATEGORY,
				severity="Info",
				result="Error",
				message="Semgrep returned invalid JSON output.",
				details=json.dumps({"stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}),
				remediation="Verify the worker Semgrep version and keep `--json` enabled.",
			)
		]

	results = []
	results.extend(_parse_semgrep_errors(payload.get("errors", [])))
	results.extend(_build_category_results(payload.get("results", [])))

	return results


def _parse_semgrep_errors(errors: list[dict]) -> list[CheckResult]:
	results = []

	for index, error in enumerate(errors, start=1):
		results.append(
			CheckResult(
				check_id=f"semgrep_error_{index}",
				check_name="Semgrep Runtime Error",
				category=DEFAULT_CATEGORY,
				severity="Info",
				result="Error",
				message=error.get("message", "Semgrep reported an error."),
				details=json.dumps(error),
				remediation="Review the error and fix the bad file or bad rule.",
			)
		)

	return results


def _build_category_results(findings: list[dict]) -> list[CheckResult]:
	"""
	group results by respective category
	correctness:[
			{
				"check_id": "correctness_frappe_manual_commit",
				"path": "frappe/core/app.py",
				"start": {
					"line": 100,
					"col": 5,
					"offset": 100
				}
			}
		]

	The result check will be like this:
	{"occurrences": [
		{"rule_id": "frappe-manual-commit", "path": "example_app/example_app/api/v2/auto_gen_api.py", "start": {"line": 535, "col": 5, "offset": 18356}, "end": {"line": 535, "col": 23, "offset": 18374}, "message": "Manually commiting a transaction is highly discouraged. Read about the transaction model implemented by Frappe Framework before adding manual commits: https://frappeframework.com/docs/user/en/api/database#database-transaction-model If you think manual commit is required then add a comment explaining why and `// nosemgrep` on the same line.", "severity": "ERROR"}]}
	"""

	findings_by_category: dict[str, list[dict]] = {category: [] for category in EXPECTED_CATEGORIES}
	for finding in findings:
		category = _get_finding_category(finding)
		if category not in findings_by_category:
			continue
		findings_by_category[category].append(finding)

	# build check results for each category
	results = []
	for category in EXPECTED_CATEGORIES:
		category_findings = findings_by_category[category]

		# if no findings for a category, return a pass result
		if not category_findings:
			results.append(
				CheckResult(
					check_id=_make_category_check_id(category),
					check_name=f"Semgrep {category}",
					category=category,
					severity=DEFAULT_SEVERITY,
					result="Pass",
					message=f"Semgrep {category} checks passed.",
				)
			)
			continue

		# blocking findings are those which have is_blocking set to true in the metadata in the semgrep rule: these are hard fail checks
		is_any_blocking_finding = any(_is_blocking_finding(finding) for finding in category_findings)
		# no need to check for internal only findings here: as they will be used when showing the results to the publisher(in mail/dashboard)

		# if there are findings for a category, return a fail result with the highest severity
		highest_severity = _highest_audit_severity(category_findings)

		# occurrences: list of findings for a category
		results.append(
			CheckResult(
				check_id=_make_category_check_id(category),
				check_name=f"Semgrep {category}",
				category=category,
				severity=highest_severity,
				result="Fail"
				if highest_severity in {"Critical", "Major"} or is_any_blocking_finding
				else "Warn",
				message=f"Semgrep {category} checks found {len(category_findings)} issue(s).",
				details=json.dumps(
					{
						"occurrences": [_serialize_finding(finding) for finding in category_findings],
					}
				),
				remediation="We observed some issues with the codebase. Please review the occurrences list and fix the issues.",
				is_blocking=is_any_blocking_finding,
				# is internal only should be false for semgrep ruleset, as none of the semgrep ruleset are just for internal purpose
				# a few rules are internal only, but we should not roll them up to declare the entire ruleset as internal only
				# is_internal_only condition will be handled when showing the results to the publisher(in mail/dashboard)
				is_internal_only=False,
			)
		)

	return results


def _get_finding_category(finding: dict) -> str:
	extra = finding.get("extra", {})
	metadata = extra.get("metadata", {})
	return metadata.get("marketplace_category", DEFAULT_CATEGORY)


def _highest_audit_severity(findings: list[dict]) -> str:
	"""
	If a finding has a mix of Critical, Major, Minor, and Info severities, return the highest severity.
	"""
	highest = "Info"

	for finding in findings:
		extra = finding.get("extra", {})
		semgrep_severity = str(extra.get("severity", "INFO")).upper()
		audit_severity = SEMGREP_TO_AUDIT_SEVERITY.get(semgrep_severity, "Info")
		if SEVERITY_ORDER[audit_severity] > SEVERITY_ORDER[highest]:
			highest = audit_severity

	return highest


def _serialize_finding(finding: dict) -> dict:
	extra = finding.get("extra", {})
	message = " ".join(extra.get("message", "").split())

	# make rule id short
	check_id = finding.get("check_id") or ""
	rule_id = re.split(r"[./]", check_id)[-1]

	return {
		"rule_id": rule_id,
		"path": finding.get("path"),
		"start": finding.get("start"),
		"end": finding.get("end"),
		"message": message,
		"severity": extra.get("severity"),
		"is_internal_only": _is_internal_only_finding(finding),
		"is_blocking": _is_blocking_finding(finding),
	}


def _make_category_check_id(category: str) -> str:
	raw = f"semgrep_{category.lower()}"
	return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_")


def _metadata(finding: dict) -> dict:
	return (finding.get("extra") or {}).get("metadata") or {}


def _is_internal_only_finding(finding: dict) -> bool:
	return bool(_metadata(finding).get("is_internal_only"))


def _is_blocking_finding(finding: dict) -> bool:
	# Only explicit true is blocking
	return _metadata(finding).get("is_blocking") is True
