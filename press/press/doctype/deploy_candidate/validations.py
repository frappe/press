from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from press.press.doctype.deploy_candidate.utils import (
	get_will_fail_checker,
)

if TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group.release_group import ReleaseGroup


def get_required_apps_from_hookpy(hooks_path: str) -> list[str]:
	"""
	Returns required_apps from an app's hooks.py file.
	"""

	with open(hooks_path) as f:
		hooks = f.read()

	for assign in ast.parse(hooks).body:
		if not isinstance(assign, ast.Assign):
			continue

		if not assign.targets:
			continue

		target = assign.targets[0]
		if not isinstance(target, ast.Name):
			continue

		if target.id != "required_apps":
			continue

		if not isinstance(assign.value, ast.List):
			return []

		return [
			v.value for v in assign.value.elts if isinstance(v, ast.Constant) and isinstance(v.value, str)
		]

	return []


def check_if_update_will_fail(rg: "ReleaseGroup", new_dc: "DeployCandidate"):
	if not (old_dcb := rg.get_last_deploy_candidate_build()):
		return

	if not old_dcb.error_key:
		return

	if not (checker := get_will_fail_checker(old_dcb.error_key)):
		return

	checker(old_dcb, new_dc)
