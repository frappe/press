import json
import os

import frappe
import semantic_version as sv

from press.marketplace.doctype.marketplace_app_audit.marketplace_app_audit import CheckResult

CATEGORY = "Compatibility"


def run_compatibility_checks(source: str, clone_dir: str) -> list[CheckResult]:
	"""
	Checks whether the app's declared Frappe version support (in pyproject.toml)
	is still compatible with all Release Groups where this source is installed.
	Example:
	- App Source was already installed on public/private benches for v15,v16.
	- but the app's pyproject.toml now declares support only for >=16.0.0,<17.0.0-dev
	- App is still installed on v15 benches. This is incompatible.
	- We need to flag this as a Critical issue.
	"""
	results: list[CheckResult] = []

	pyproject = _safe_load_pyproject(os.path.join(clone_dir, "pyproject.toml"))
	if pyproject is None:
		return results

	frappe_spec_str = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies", {}).get("frappe")
	if not frappe_spec_str:
		return results

	supported_versions = _get_supported_frappe_versions(frappe_spec_str)
	if not supported_versions:
		return results

	results.append(check_bench_compatibility(source, supported_versions, frappe_spec_str))
	return results


def _safe_load_pyproject(pyproject_path: str) -> dict | None:
	from tomli import TOMLDecodeError, load

	try:
		with open(pyproject_path, "rb") as f:
			return load(f)
	except (TOMLDecodeError, FileNotFoundError):
		return None


def _get_supported_frappe_versions(frappe_spec_str: str) -> list[str] | None:
	"""
	Resolve a semver specifier like ">=15.0.0-dev,<=16.0.0-dev" into
	Frappe Version names like ["Version 15", "Version 16"].

	Uses the same NpmSpec logic as map_frappe_version in app.py,
	but without frappe.throw — returns None on invalid input so
	versioning checks can report the error instead.
	"""
	try:
		spec = sv.NpmSpec(frappe_spec_str.replace(" ", "").replace(",", " "))
	except ValueError:
		return None

	frappe_versions = frappe.get_all(
		"Frappe Version",
		{"public": True},
		["name", "number", "status"],
	)

	matched = []
	for version in frappe_versions:
		if spec.match(sv.Version(f"{version['number']}.0.0")):
			matched.append(str(version["name"]))

	return matched or None


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
		f"App declares support for {supported_versions} "
		f"but is installed on benches with incompatible versions: {affected_versions}.",
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
	)
