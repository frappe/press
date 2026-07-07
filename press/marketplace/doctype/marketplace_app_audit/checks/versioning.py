import json
import os
from pathlib import Path

from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult
from press.press.doctype.app_release.app_release import check_pyproject_syntax

CATEGORY = "Versioning"
DOCS_URL = "https://docs.frappe.io/cloud/custom-apps/app-versioning/versioning"


# Summary of checks present in versioning.py with their respective severity levels:
# - pyproject.toml exists: Critical
# - pyproject.toml syntax is valid: Critical
# - [tool.bench.frappe-dependencies] section exists: Critical
# - frappe version specifier is valid: Critical
# - no frappe in [project.dependencies]: Major
# - no other common apps in [project.dependencies]: Major
# - app version declared: Minor
# - no dual dependency files: Info


def run_versioning_checks(clone_dir: str) -> list[CheckResult]:
	results = []
	pyproject_path = os.path.join(clone_dir, "pyproject.toml")

	# Gate check 1 - pyproject.toml exists
	results.append(check_pyproject_exists(pyproject_path))
	# if pyproject.toml does not exist, skip the rest of the checks
	if results[-1].result == "Fail":
		return results

	# Gate check 2 - pyproject.toml syntax is valid
	results.append(check_pyproject_valid_syntax(clone_dir))

	pyproject = _safe_load_pyproject(pyproject_path)
	if pyproject is None:
		return results

	# Other checks now that we know pyproject.toml exists and has valid syntax
	deps_result = check_frappe_deps_section(pyproject)
	if deps_result.result == "Fail":
		results.append(deps_result)
		# skip the rest of the checks
		return results

	results.append(check_frappe_version_specifier(pyproject))
	results.append(check_no_frappe_in_project_deps(pyproject))
	results.append(check_no_other_apps_in_project_deps(pyproject))
	results.append(check_version_declared(pyproject, clone_dir))
	results.append(check_no_dual_dependency_files(clone_dir))
	results.append(check_no_hard_pinned_frappe_version(pyproject))

	return results


def _safe_load_pyproject(pyproject_path: str) -> dict | None:
	from tomli import TOMLDecodeError, load

	try:
		with open(pyproject_path, "rb") as f:
			return load(f)
	except TOMLDecodeError:
		return None


def check_pyproject_exists(pyproject_path: str) -> CheckResult:
	if not os.path.exists(pyproject_path):
		return CheckResult(
			check_id="ver_pyproject_exists",
			check_name="pyproject.toml exists",
			category=CATEGORY,
			result="Fail",
			severity="Critical",
			message="pyproject.toml not found at the root of the app",
			details="pyproject.toml not found at the root of the app",
			remediation="Please add a pyproject.toml file at the root of the app",
		)

	return CheckResult(
		check_id="ver_pyproject_exists",
		check_name="pyproject.toml exists",
		category=CATEGORY,
		result="Pass",
		severity="Critical",
		message="pyproject.toml found at the root of the app",
	)


def check_pyproject_valid_syntax(clone_dir: str) -> CheckResult:
	syntax_error = check_pyproject_syntax(clone_dir)
	if not syntax_error:
		return CheckResult(
			check_id="ver_pyproject_valid_syntax",
			check_name="pyproject.toml Valid Syntax",
			category=CATEGORY,
			severity="Critical",
			result="Pass",
			message="pyproject.toml has valid TOML syntax",
		)
	return CheckResult(
		check_id="ver_pyproject_valid_syntax",
		check_name="pyproject.toml Valid Syntax",
		category=CATEGORY,
		severity="Critical",
		result="Fail",
		message="pyproject.toml has invalid TOML syntax",
		details=json.dumps({"syntax_error": syntax_error}),
		remediation="Fix the TOML syntax errors in pyproject.toml. Validate locally with: python -c \"import tomli; tomli.load(open('pyproject.toml','rb'))\"",
	)


def check_frappe_deps_section(pyproject: dict) -> CheckResult:
	frappe_deps = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies")

	if frappe_deps:
		return CheckResult(
			check_id="ver_frappe_deps_section",
			check_name="[tool.bench.frappe-dependencies] Section",
			category=CATEGORY,
			severity="Critical",
			result="Pass",
			message="[tool.bench.frappe-dependencies] section found",
		)

	return CheckResult(
		check_id="ver_frappe_deps_section",
		check_name="[tool.bench.frappe-dependencies] Section",
		category=CATEGORY,
		severity="Critical",
		result="Fail",
		message="Missing [tool.bench.frappe-dependencies] section in pyproject.toml",
		remediation=(
			"Add this section to your pyproject.toml:\n\n"
			"[tool.bench.frappe-dependencies]\n"
			'frappe = ">=16.0.0-dev,<=17.0.0-dev"\n\n'
			f"See {DOCS_URL}"
		),
	)


def check_frappe_version_specifier(pyproject: dict) -> CheckResult:
	import semantic_version as sv

	frappe_deps = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies", {})

	frappe_spec = frappe_deps.get("frappe")
	if not frappe_spec:
		return CheckResult(
			check_id="ver_frappe_version_specifier",
			check_name="Frappe Version Specifier",
			category=CATEGORY,
			severity="Critical",
			result="Fail",
			message="No 'frappe' key in [tool.bench.frappe-dependencies]",
			details=json.dumps({"declared_keys": list(frappe_deps.keys())}),
			remediation=('Add frappe = ">=16.0.0-dev,<=17.0.0-dev" under [tool.bench.frappe-dependencies]'),
		)

	try:
		sv.SimpleSpec(frappe_spec)
	except ValueError as e:
		return CheckResult(
			check_id="ver_frappe_version_specifier",
			check_name="Frappe Version Specifier",
			category=CATEGORY,
			severity="Critical",
			result="Fail",
			message=f"Invalid version specifier: {frappe_spec}",
			details=json.dumps({"specifier": frappe_spec, "error": str(e)}),
			remediation='Use a valid semver range like ">=16.0.0-dev,<=17.0.0-dev"',
		)

	return CheckResult(
		check_id="ver_frappe_version_specifier",
		check_name="Frappe Version Specifier",
		category=CATEGORY,
		severity="Critical",
		result="Pass",
		message=f"Valid frappe version specifier: {frappe_spec}",
		details=json.dumps({"specifier": frappe_spec}),
	)


def check_no_frappe_in_project_deps(pyproject: dict) -> CheckResult:
	"""
	frappe is injected by bench — listing it in [project.dependencies]
	causes duplicate installs and 'frappe not found' pip errors.
	"""

	project_deps = pyproject.get("project", {}).get("dependencies", [])
	frappe_entries = [dep for dep in project_deps if dep.lower().startswith("frappe")]

	if not frappe_entries:
		return CheckResult(
			check_id="ver_no_frappe_in_project_deps",
			check_name="No frappe in [project.dependencies]",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="frappe is not in [project.dependencies]",
		)

	return CheckResult(
		check_id="ver_no_frappe_in_project_deps",
		check_name="No frappe in [project.dependencies]",
		category=CATEGORY,
		severity="Major",
		result="Fail",
		message="frappe found in [project.dependencies] — this will cause build failures",
		details=json.dumps({"found_entries": frappe_entries}),
		remediation=(
			"Remove frappe from [project.dependencies]. "
			"Frappe is provided by the bench environment. "
			"Declare version specifier in [tool.bench.frappe-dependencies] instead."
		),
	)


def check_no_other_apps_in_project_deps(pyproject: dict) -> CheckResult:
	project_deps = pyproject.get("project", {}).get("dependencies", [])
	other_common_app_names = ["erpnext", "frappe-bench", "crm", "hrms"]
	other_app_entries = [dep for dep in project_deps if dep.lower() in other_common_app_names]
	if other_app_entries:
		return CheckResult(
			check_id="ver_no_other_apps_in_project_deps",
			check_name="No other common apps in [project.dependencies]",
			category=CATEGORY,
			severity="Major",
			result="Fail",
			message="Other common apps found in [project.dependencies]",
			details=json.dumps({"found_entries": other_app_entries}),
			remediation=(
				"Remove other common apps from [project.dependencies]. "
				"These are provided by the bench environment. "
			),
		)

	return CheckResult(
		check_id="ver_no_other_apps_in_project_deps",
		check_name="No other common apps in [project.dependencies]",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message="No other common apps found in [project.dependencies]",
	)


def _get_version_from_init_files(clone_dir: str) -> str | None:
	"""Look for __version__ or VERSION in __init__.py files (one level deep)."""
	for entry in Path(clone_dir).iterdir():
		if not entry.is_dir():
			continue

		init_path = entry / "__init__.py"
		if not init_path.is_file():
			continue

		with init_path.open("r", encoding="utf-8") as f:
			for line in f:
				if line.startswith(("__version__ =", "VERSION =")):
					return line.split("=", 1)[1].strip().strip("\"'") or None

	return None


def check_version_declared(pyproject: dict, clone_dir: str) -> CheckResult:
	version = pyproject.get("project", {}).get("version")

	if not version:
		version = _get_version_from_init_files(clone_dir)

	if version:
		return CheckResult(
			check_id="ver_app_version_declared",
			check_name="App Version Declared",
			category=CATEGORY,
			severity="Minor",
			result="Pass",
			message=f"App version: {version}",
		)

	return CheckResult(
		check_id="ver_app_version_declared",
		check_name="App Version Declared",
		category=CATEGORY,
		severity="Minor",
		result="Warn",
		message="No version found in pyproject.toml or __init__.py",
		remediation=(
			'Add version under [project] in pyproject.toml, e.g. version = "1.0.0", '
			"or set __version__ in your app's __init__.py"
		),
	)


def check_no_dual_dependency_files(clone_dir: str) -> CheckResult:
	"""
	Warns when both pyproject.toml
	and requirements.txt exist. pyproject.toml takes precedence, but
	having both creates confusion about which drives pip installs.
	"""

	has_requirements = os.path.isfile(os.path.join(clone_dir, "requirements.txt"))

	if not has_requirements:
		return CheckResult(
			check_id="ver_no_dual_dep_files",
			check_name="No Dual Dependency Files",
			category=CATEGORY,
			severity="Info",
			result="Pass",
			message="Only pyproject.toml present (no requirements.txt)",
		)

	return CheckResult(
		check_id="ver_no_dual_dep_files",
		check_name="No Dual Dependency Files",
		category=CATEGORY,
		severity="Info",
		result="Warn",
		message="Both pyproject.toml and requirements.txt found — pyproject.toml takes precedence",
		remediation=(
			"Consider removing requirements.txt and managing all dependencies in pyproject.toml "
			"to avoid confusion about which file drives pip installs."
		),
	)


def check_no_hard_pinned_frappe_version(pyproject: dict) -> CheckResult:
	"""A hard pin like frappe = "16.5.3" breaks on every Frappe patch release."""
	range_operators = (">=", "<=", ">", "<", "!=", ",")

	frappe_spec = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies", {}).get("frappe", "")

	if not frappe_spec:
		return CheckResult(
			check_id="ver_no_hard_pinned_frappe",
			check_name="No Hard-Pinned Frappe Version",
			category=CATEGORY,
			severity="Minor",
			result="Skipped",
			message="Skipped — no frappe specifier found",
		)

	is_hard_pinned = not any(op in frappe_spec for op in range_operators)

	if not is_hard_pinned:
		return CheckResult(
			check_id="ver_no_hard_pinned_frappe",
			check_name="No Hard-Pinned Frappe Version",
			category=CATEGORY,
			severity="Minor",
			result="Pass",
			message=f"Frappe version uses a range: {frappe_spec}",
		)

	return CheckResult(
		check_id="ver_no_hard_pinned_frappe",
		check_name="No Hard-Pinned Frappe Version",
		category=CATEGORY,
		severity="Minor",
		result="Warn",
		message=f"Frappe is hard-pinned to: {frappe_spec}",
		remediation=(
			'Use a version range instead of an exact pin, e.g. ">=16.0.0-dev,<=17.0.0-dev". '
			"Exact pins break on every Frappe patch release."
		),
	)
