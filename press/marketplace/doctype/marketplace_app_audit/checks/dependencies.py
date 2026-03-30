import ast
import json
import os
from pathlib import Path

from press.marketplace.doctype.marketplace_app_audit.checks.utils import (
	_extract_string_assignment,
	_get_call_name,
)
from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult
from press.utils import get_filepath

CATEGORY = "Dependencies"

# Check summary with severity levels:
# - hooks.py exists: Critical (gate)
# - hooks.py valid syntax: Critical (gate)
# - no symlinks in app tree: Critical
# - no print/side-effects in __init__.py: Major
# - app_name matches directory: Major
# - required_apps well-formed: Major


def run_dependency_checks(clone_dir: str) -> list[CheckResult]:
	results = []

	# Gate check 1 - hooks.py exists
	hooks_path = get_filepath(clone_dir, "hooks.py", 2)
	results.append(check_hooks_exists(hooks_path))
	if results[-1].result == "Fail":
		return results

	# Gate check 2 - hooks.py has valid syntax
	results.append(check_hooks_syntax(hooks_path))
	if results[-1].result == "Fail":
		return results

	results.append(check_no_symlinks(clone_dir))
	results.append(check_init_no_side_effects(clone_dir))
	results.append(check_app_name_consistency(clone_dir, hooks_path))
	results.append(check_required_apps(hooks_path))

	return results


def check_hooks_exists(hooks_path: str | None) -> CheckResult:
	if hooks_path is None:
		return CheckResult(
			check_id="dep_hooks_exists",
			check_name="hooks.py Exists",
			category=CATEGORY,
			severity="Critical",
			result="Fail",
			message="hooks.py not found in the app",
			remediation="Add a hooks.py file in the app's root package directory.",
		)

	return CheckResult(
		check_id="dep_hooks_exists",
		check_name="hooks.py Exists",
		category=CATEGORY,
		severity="Critical",
		result="Pass",
		message="hooks.py found",
	)


def check_hooks_syntax(hooks_path: str) -> CheckResult:
	try:
		with open(hooks_path) as f:
			ast.parse(f.read(), filename=hooks_path)
	except SyntaxError as e:
		return CheckResult(
			check_id="dep_hooks_syntax",
			check_name="hooks.py Valid Syntax",
			category=CATEGORY,
			severity="Critical",
			result="Fail",
			message="hooks.py has invalid Python syntax",
			details=json.dumps({"line": e.lineno, "error": str(e.msg)}),
			remediation="Fix the syntax error and verify locally with: python -c \"import ast; ast.parse(open('hooks.py').read())\"",
		)

	return CheckResult(
		check_id="dep_hooks_syntax",
		check_name="hooks.py Valid Syntax",
		category=CATEGORY,
		severity="Critical",
		result="Pass",
		message="hooks.py has valid Python syntax",
	)


def check_no_symlinks(clone_dir: str) -> CheckResult:
	symlinks = []
	for root, dirs, files in os.walk(clone_dir):
		for name in dirs + files:
			full_path = os.path.join(root, name)
			if os.path.islink(full_path):
				symlinks.append(os.path.relpath(full_path, clone_dir))

	if symlinks:
		return CheckResult(
			check_id="dep_no_symlinks",
			check_name="No Symlinks",
			category=CATEGORY,
			severity="Critical",
			result="Fail",
			message=f"Found {len(symlinks)} symlink(s) in the app — symlinks cause build errors",
			details=json.dumps({"symlinks": symlinks[:20]}),
			remediation="Replace symlinks with actual files or proper Python/JS imports.",
		)

	return CheckResult(
		check_id="dep_no_symlinks",
		check_name="No Symlinks",
		category=CATEGORY,
		severity="Critical",
		result="Pass",
		message="No symlinks found",
	)


def check_init_no_side_effects(clone_dir: str) -> CheckResult:  # noqa: C901
	"""
	Detects print calls and other bare function calls at the top level
	of __init__.py files. These pollute bench CLI output since every
	bench command imports all installed apps.
	"""
	violations = []

	for entry in Path(clone_dir).iterdir():
		if not entry.is_dir():
			continue
		init_path = entry / "__init__.py"
		if not init_path.is_file():
			continue

		try:
			tree = ast.parse(init_path.read_text(encoding="utf-8"))
		except SyntaxError:
			continue

		for node in tree.body:
			if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
				continue
			func = node.value.func
			func_name = _get_call_name(func)
			if func_name:
				violations.append(
					{"file": entry.name + "/__init__.py", "line": node.lineno, "call": func_name}
				)

	if violations:
		return CheckResult(
			check_id="dep_init_side_effects",
			check_name="No Side-Effects in __init__.py",
			category=CATEGORY,
			severity="Major",
			result="Fail",
			message=f"Found {len(violations)} top-level function call(s) in __init__.py that may produce output or side-effects",
			details=json.dumps({"violations": violations[:20]}),
			remediation="Remove print statements and other bare function calls from __init__.py. "
			"These run on every bench command and can break CLI output.",
		)

	return CheckResult(
		check_id="dep_init_side_effects",
		check_name="No Side-Effects in __init__.py",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message="No side-effect calls found in __init__.py files",
	)


def check_app_name_consistency(clone_dir: str, hooks_path: str) -> CheckResult:
	"""
	The app_name in hooks.py must match the Python package directory name
	so that bench can locate the app correctly.
	"""
	hooks_app_name = _extract_string_assignment(hooks_path, "app_name")

	if hooks_app_name is None:
		return CheckResult(
			check_id="dep_app_name_consistency",
			check_name="app_name Consistency",
			category=CATEGORY,
			severity="Major",
			result="Fail",
			message="No app_name variable found in hooks.py",
			remediation='Add app_name = "your_app" in hooks.py matching your package directory name.',
		)

	# The package dir is the directory that contains hooks.py
	package_dir = Path(hooks_path).parent.name

	if hooks_app_name != package_dir:
		return CheckResult(
			check_id="dep_app_name_consistency",
			check_name="app_name Consistency",
			category=CATEGORY,
			severity="Major",
			result="Fail",
			message=f"app_name '{hooks_app_name}' in hooks.py does not match package directory '{package_dir}'",
			details=json.dumps({"hooks_app_name": hooks_app_name, "package_dir": package_dir}),
			remediation=f"Set app_name = \"{package_dir}\" in hooks.py, or rename your package directory to '{hooks_app_name}'.",
		)

	return CheckResult(
		check_id="dep_app_name_consistency",
		check_name="app_name Consistency",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message=f"app_name '{hooks_app_name}' matches package directory",
	)


def check_required_apps(hooks_path: str) -> CheckResult:
	"""
	Validates that required_apps in hooks.py is well-formed:
	a list of non-empty, unique strings without 'frappe' (implicitly required).
	"""
	from press.press.doctype.deploy_candidate.validations import get_required_apps_from_hookpy

	try:
		required_apps = get_required_apps_from_hookpy(hooks_path)
	except Exception:
		return CheckResult(
			check_id="dep_required_apps",
			check_name="required_apps Valid",
			category=CATEGORY,
			severity="Major",
			result="Fail",
			message="Could not parse required_apps from hooks.py",
			remediation='Ensure required_apps is a simple list of string literals, e.g. required_apps = ["erpnext"]',
		)

	if not required_apps:
		return CheckResult(
			check_id="dep_required_apps",
			check_name="required_apps Valid",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="No required_apps declared (or empty list)",
		)

	issues = []

	if "frappe" in required_apps:
		issues.append("'frappe' is listed in required_apps but is always implicitly available")

	empty_entries = [app for app in required_apps if not app.strip()]
	if empty_entries:
		issues.append(f"{len(empty_entries)} empty string(s) in required_apps")

	duplicates = [app for app in required_apps if required_apps.count(app) > 1]
	if duplicates:
		issues.append(f"Duplicate entries: {list(set(duplicates))}")

	if issues:
		return CheckResult(
			check_id="dep_required_apps",
			check_name="required_apps Valid",
			category=CATEGORY,
			severity="Major",
			result="Warn",
			message="required_apps has issues",
			details=json.dumps({"issues": issues, "required_apps": required_apps}),
			remediation="Fix the listed issues in required_apps. Remove 'frappe', duplicates, and empty entries.",
		)

	return CheckResult(
		check_id="dep_required_apps",
		check_name="required_apps Valid",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message=f"required_apps is well-formed: {required_apps}",
	)
