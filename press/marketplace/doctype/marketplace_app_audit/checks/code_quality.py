import ast
import json

from press.marketplace.doctype.marketplace_app_audit.checks.utils import (
	_extract_dict_string_keys,
	_extract_top_level_assignments,
)
from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult
from press.utils import get_filepath

CATEGORY = "Code Quality"


# run_code_quality_checks(clone_dir: str) -> list[CheckResult]:
# get hooks_path, parse into AST, extract assignments
#  check_override_doctype_class(assignments)
#  check_override_whitelisted_methods(assignments)
#  check_doc_events_wildcard(assignments)
#  check_fixtures_usage(assignments) ?
#  check_missing_uninstall_hook(assignments) ?


def run_code_quality_checks(clone_dir: str) -> list[CheckResult]:
	results = []

	hooks_path = get_filepath(clone_dir, "hooks.py", 2)
	if not hooks_path:
		return []

	with open(hooks_path) as f:
		tree = ast.parse(f.read())
	assignments = _extract_top_level_assignments(tree)

	results.append(check_override_doctype_class(assignments))
	results.append(check_override_whitelisted_methods(assignments))
	results.append(check_doc_events_wildcard(assignments))

	return results


def check_override_doctype_class(assignments: dict[str, ast.expr]) -> CheckResult:
	"""
	Check if the app overrides the doctype class.
	Overriding doctypes is allowed by the framework, so we should not Fail anything here.
	But a warning should be issued if the app overrides any core doctype to just give a heads up to the app reviewer.
	"""

	override_doctype_class = assignments.get("override_doctype_class")

	if override_doctype_class is None:
		return CheckResult(
			check_id="code_quality_override_doctype_class",
			check_name="Override Doctype Class",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="The app does not override any doctypes.",
		)

	# if present and is ast.Dict -> extract the overridden doctype names → Warn with list of doctypes in details.
	if isinstance(override_doctype_class, ast.Dict):
		overridden_doctypes = _extract_dict_string_keys(override_doctype_class)
		return CheckResult(
			check_id="code_quality_override_doctype_class",
			check_name="Override Doctype Class",
			category=CATEGORY,
			severity="Major",
			result="Warn",
			message="The app overrides the following doctypes: " + ", ".join(overridden_doctypes),
			details=json.dumps({"overridden_doctypes": overridden_doctypes}),
			remediation="""
				Use extend_doctype_class (Frappe v16+) or doc_events hooks instead if possible.
				Full class overrides miss upstream bug fixes and conflict with other apps
				Go through the docs to understand the difference between the two approaches - https://docs.frappe.io/framework/user/en/python-api/hooks#override-doctype-class
			""",
		)
	return CheckResult(
		check_id="code_quality_override_doctype_class",
		check_name="Override Doctype Class",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message="override_doctype_class is present but not a dict literal; check skipped.",
	)


def check_override_whitelisted_methods(assignments: dict[str, ast.expr]) -> CheckResult:
	"""
	Check if the app overrides any whitelisted methods.
	Overriding whitelisted methods is allowed by the framework, so we should not Fail anything here.
	But a warning should be issued if the app overrides any whitelisted method to just give a heads up to the app reviewer.
	"""

	override_whitelisted_methods = assignments.get("override_whitelisted_methods")
	if override_whitelisted_methods is None:
		return CheckResult(
			check_id="code_quality_override_whitelisted_methods",
			check_name="Override Whitelisted Methods",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="The app does not override any whitelisted methods.",
		)

	if isinstance(override_whitelisted_methods, ast.Dict):
		overridden_methods = _extract_dict_string_keys(override_whitelisted_methods)
		return CheckResult(
			check_id="code_quality_override_whitelisted_methods",
			check_name="Override Whitelisted Methods",
			category=CATEGORY,
			severity="Major",
			result="Warn",
			message="The app overrides the following whitelisted methods: " + ", ".join(overridden_methods),
			details=json.dumps({"overridden_methods": overridden_methods}),
			remediation="""
				These overrides should be reviewed for compatibility with framework updates.
				The method should have the same signature as the original method.
            """,
		)

	return CheckResult(
		check_id="code_quality_override_whitelisted_methods",
		check_name="Override Whitelisted Methods",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message="override_whitelisted_methods is present but not a dict literal; check skipped.",
	)


def check_doc_events_wildcard(assignments: dict[str, ast.expr]) -> CheckResult:
	"""
	Check if the app uses the wildcard(*) doc_events hook.
	Wildcard doc_events will run after any DocType record like -
	"*": {
		# will run after any DocType record is inserted into database
		"after_insert": "app.crud_events.after_insert_all",
	}
	This is generally regarded as bad practice as it can lead to performance issues and unexpected behavior.
	The app should use the specific doc_events hooks instead. Warn the reviewer of such behavior if found.
	"""
	doc_events = assignments.get("doc_events")

	if doc_events is None:
		return CheckResult(
			check_id="code_quality_doc_events_wildcard",
			check_name="Doc Events Wildcard",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="The app does not use any doc_events hooks.",
		)

	# If doc_events is not a dict literal, don't crash; just skip warning.
	if not isinstance(doc_events, ast.Dict):
		return CheckResult(
			check_id="code_quality_doc_events_wildcard",
			check_name="Doc Events Wildcard",
			category=CATEGORY,
			severity="Major",
			result="Pass",
			message="doc_events is present but not a dict literal; wildcard check skipped.",
		)

	for key_node, value_node in zip(doc_events.keys, doc_events.values, strict=False):
		if isinstance(key_node, ast.Constant) and key_node.value == "*":
			event_names = _extract_dict_string_keys(value_node)
			return CheckResult(
				check_id="code_quality_doc_events_wildcard",
				check_name="Doc Events Wildcard",
				category=CATEGORY,
				severity="Major",
				result="Warn",
				message="The app uses wildcard doc_events ('*').",
				details=json.dumps({"event_names": event_names}),
				remediation=(
					"Wildcard doc_events fire on every document operation across all DocTypes, "
					"which can impact performance on shared benches. Target specific DocTypes instead."
				),
			)

	return CheckResult(
		check_id="code_quality_doc_events_wildcard",
		check_name="Doc Events Wildcard",
		category=CATEGORY,
		severity="Major",
		result="Pass",
		message="The app does not use wildcard doc_events ('*').",
	)
