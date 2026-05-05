import json
import os

import frappe

from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult
from press.press.doctype.app.app import map_frappe_version

CATEGORY = "Compatibility"


def run_compatibility_checks(marketplace_app: str, source: str, clone_dir: str) -> list[CheckResult]:
	"""
	Runs when pyproject has a bounded frappe spec.

	1. Bench check: release groups with this source must use a Frappe version in the resolved list.
	2. Registration check: Marketplace App Version (parent + source) must be in that same list.

	Both use ease_versioning_constrains=True so behaviour matches Marketplace add_version / change_branch.
	If the source is not listed on the marketplace app, (2) is skipped.
	"""
	results: list[CheckResult] = []

	pyproject = _safe_load_pyproject(os.path.join(clone_dir, "pyproject.toml"))
	if pyproject is None:
		return results

	frappe_spec_str = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies", {}).get("frappe")
	if not frappe_spec_str:
		return results

	# Align with Marketplace App add_version / change_branch: allow lower bounds like
	# >=16.15.0,<17 to count as supporting "Version 16" (lower-bound major match).
	supported_versions = _frappe_versions_for_spec(frappe_spec_str, ease_versioning_constrains=True)
	if not supported_versions:
		return results

	results.append(check_bench_compatibility(source, supported_versions, frappe_spec_str))
	reg = check_app_source_compatibility(marketplace_app, source, frappe_spec_str, supported_versions)
	if reg is not None:
		results.append(reg)
	return results


def _safe_load_pyproject(pyproject_path: str) -> dict | None:
	from tomli import TOMLDecodeError, load

	try:
		with open(pyproject_path, "rb") as f:
			return load(f)
	except (TOMLDecodeError, FileNotFoundError):
		return None


def _frappe_versions_for_spec(frappe_spec_str: str, *, ease_versioning_constrains: bool) -> list[str] | None:
	"""
	Resolve pyproject frappe NPM spec to Frappe Version names using the same logic as
	validate_frappe_version_for_branch / map_frappe_version.
	"""
	try:
		frappe_versions = frappe.get_all(
			"Frappe Version",
			{"public": True},
			["name", "number", "status"],
		)
		return map_frappe_version(
			frappe_spec_str,
			frappe_versions,
			"Marketplace audit",
			ease_versioning_constrains,
		)
	except Exception:
		return None


def check_bench_compatibility(source: str, supported_versions: list[str], frappe_spec: str) -> CheckResult:
	"""
	Find all enabled Release Groups using this exact source where the
	bench's Frappe version is no longer in the app's supported set.

	Why filter by source (not app name): a marketplace app can have
	different sources per Frappe version (e.g. branch "main" for v16,
	branch "version-15" for v15). Only benches using THIS source are
	affected by THIS source's pyproject.toml change.
	"""
	rg = frappe.qb.DocType("Release Group")
	rga = frappe.qb.DocType("Release Group App")

	incompatible = (
		frappe.qb.from_(rg)
		.join(rga)
		.on(rga.parent == rg.name)
		.where(rg.enabled == 1)
		.where(rga.source == source)
		.where(rg.version.notin(supported_versions))
		.select(rg.name, rg.version, rg.public)
		.run(as_dict=True)
	)

	if not incompatible:
		return CheckResult(
			check_id="compat_bench_versions",
			check_name="Bench Version Compatibility",
			category=CATEGORY,
			result="Pass",
			severity="Critical",
			message=f"App supports {supported_versions} — all installed benches are compatible",
			is_internal_only=True,
		)

	public_benches = [b for b in incompatible if b.public]
	private_benches = [b for b in incompatible if not b.public]
	affected_versions = sorted(set(b.version for b in incompatible))

	severity = "Critical"

	details = {
		"supported_versions": supported_versions,
		"frappe_specifier": frappe_spec,
		"incompatible_versions": affected_versions,
		"public_benches_affected": len(public_benches),
		"private_benches_affected": len(private_benches),
		"sample_benches": [b.name for b in incompatible[:10]],
	}

	message_parts = [
		f"App declares support for {supported_versions} but is installed on benches with incompatible versions: {affected_versions}.",
	]
	if public_benches:
		message_parts.append(f"{len(public_benches)} public bench(es) affected — deployments will fail.")
	if private_benches:
		message_parts.append(f"{len(private_benches)} private bench(es) also affected.")

	return CheckResult(
		check_id="compat_bench_versions",
		check_name="Bench Version Compatibility",
		category=CATEGORY,
		result="Fail",
		severity=severity,
		message=" ".join(message_parts),
		details=json.dumps(details),
		remediation=(
			f'Your pyproject.toml declares frappe = "{frappe_spec}" which does not cover {affected_versions}. '
			"Either widen the version range to include these versions, or coordinate removing "
			"the app from incompatible benches before releasing."
		),
		is_internal_only=True,
		is_blocking=True,
	)


def check_app_source_compatibility(
	marketplace_app: str,
	source: str,
	frappe_spec: str,
	supported_versions: list[str],
) -> CheckResult | None:
	"""
	Ensure the Frappe Version this source is registered under on the marketplace app
	is among the versions supported by this clone's pyproject.toml.

	Uses the same eased mapping as add_version / change_branch so specs like
	>=16.15.0,<17.0.0 still count as supporting Version 16.
	"""
	registered = frappe.db.get_value(
		"Marketplace App Version",
		{"parent": marketplace_app, "source": source},
		"version",
	)
	if not registered:
		return None

	if registered in supported_versions:
		return CheckResult(
			check_id="compat_registered_source_version",
			check_name="Registered source vs pyproject Frappe version",
			category=CATEGORY,
			result="Pass",
			severity="Critical",
			message=(
				f"pyproject.toml is compatible with marketplace registration for {registered} on this source."
			),
			is_internal_only=False,
			is_blocking=False,
		)

	details = {
		"registered_frappe_version": registered,
		"supported_versions_from_spec": supported_versions,
		"frappe_specifier": frappe_spec,
	}
	return CheckResult(
		check_id="compat_registered_source_version",
		check_name="Registered source vs pyproject Frappe version",
		category=CATEGORY,
		result="Fail",
		severity="Critical",
		message=(
			f"This source is registered for {registered}, but "
			f'pyproject.toml frappe = "{frappe_spec}" '
			f"does not include that version (resolved: {supported_versions})."
		),
		details=json.dumps(details),
		remediation=(
			f"Update [tool.bench.frappe-dependencies].frappe to cover {registered}, "
			"or change which Frappe version this App Source is linked to on the marketplace app."
		),
		is_internal_only=False,
		is_blocking=True,
	)
