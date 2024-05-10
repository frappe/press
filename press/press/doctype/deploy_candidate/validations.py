import ast
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import frappe
import semantic_version as sv
from press.press.doctype.deploy_candidate.utils import (
	PackageManagerFiles,
	PackageManagers,
)
from press.utils import get_filepath, log_error

if TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


class PreBuildValidations:
	dc: "DeployCandidate"
	pmf: PackageManagerFiles

	def __init__(self, dc: "DeployCandidate", pmf: PackageManagerFiles):
		self.dc = dc
		self.pmf = pmf

	def validate(self):
		self._validate_repos()
		self._validate_python_requirement()
		self._validate_node_requirement()
		self._validate_frappe_dependencies()
		self._validate_required_apps()

	def _validate_repos(self):
		for app in self.dc.apps:
			if frappe.get_value(app.release, "invalid_release"):
				reason = frappe.get_value(app.release, "invalidation_reason")

				# Do not change message without updating deploy_notifications.py
				raise Exception(
					"Invalid release found",
					app.app,
					app.hash,
					reason,
				)

	def _validate_python_requirement(self):
		actual = self.dc.get_dependency_version("python")
		for app, pm in self.pmf.items():
			self._validate_python_version(app, actual, pm)

	def _validate_python_version(self, app: str, actual: str, pm: PackageManagers):
		expected = pm["pyproject"].get("project", {}).get("requires-python")
		if expected is None or check_version(actual, expected):
			return

		# Do not change args without updating deploy_notifications.py
		raise Exception(
			"Incompatible Python version found",
			app,
			actual,
			expected,
		)

	def _validate_node_requirement(self):
		actual = self.dc.get_dependency_version("node")
		for app, pm in self.pmf.items():
			self._validate_node_version(app, actual, pm)

	def _validate_node_version(self, app: str, actual: str, pm: PackageManagers):
		for pckj in pm["packagejsons"]:
			expected = pckj.get("engines", {}).get("node")
			if expected is None or check_version(actual, expected):
				continue

			package_name = pckj.get("name")

			# Do not change args without updating deploy_notifications.py
			raise Exception(
				"Incompatible Node version found",
				app,
				actual,
				expected,
				package_name,
			)

	def _validate_frappe_dependencies(self):
		for app, pm in self.pmf.items():
			if (pypr := pm["pyproject"]) is None:
				continue

			frappe_deps = pypr.get("tool", {}).get("bench", {}).get("frappe-dependencies")
			if not frappe_deps:
				continue

			self._check_frappe_dependencies(app, frappe_deps)

	def _validate_required_apps(self):
		for app, pm in self.pmf.items():
			hooks_path = get_filepath(
				pm["repo_path"],
				"hooks.py",
				2,
			)
			if hooks_path is None:
				continue

			try:
				required_apps = get_required_apps_from_hookpy(hooks_path)
			except Exception:
				log_error(
					"Failed to get required apps from hooks.py",
					hooks_path=hooks_path,
					doc=self.dc,
				)
				continue

			self._check_required_apps(app, required_apps)

	def _check_required_apps(self, app: str, required_apps: list[str]):
		for ra in required_apps:
			if self.dc.has_app(ra):
				continue

			# Do not change args without updating deploy_notifications.py
			raise Exception(
				"Required app not found",
				app,
				ra,
			)

	def _check_frappe_dependencies(self, app: str, frappe_deps: dict[str, str]):
		for dep_app, actual in frappe_deps.items():
			expected = self._get_app_version(dep_app)
			if not expected or sv.Version(expected) in sv.SimpleSpec(actual):
				continue

			# Do not change args without updating deploy_notifications.py
			raise Exception(
				"Incompatible app version found",
				app,
				dep_app,
				actual,
				expected,
			)

	def _get_app_version(self, app: str) -> Optional[str]:
		pm = self.pmf[app]
		pyproject = pm["pyproject"] or {}
		version = pyproject.get("project", {}).get("version")

		if isinstance(version, str):
			return version

		init_path = Path(pm["repo_path"]) / app / "__init__.py"
		if not init_path.is_file():
			return None

		with init_path.open("r", encoding="utf-8") as init:
			for line in init:
				if not (line.startswith("__version__ =") or line.startswith("VERSION =")):
					continue

				if version := line.split("=")[1].strip().strip("\"'"):
					return version

				break

		return None


def check_version(actual: str, expected: str) -> bool:
	# Python version mentions on press dont mention the patch version.
	if actual.count(".") == 1:
		actual += ".0"

	sv_actual = sv.Version(actual)
	sv_expected = sv.SimpleSpec(expected)

	return sv_actual in sv_expected


def get_required_apps_from_hookpy(hooks_path: str) -> list[str]:
	"""
	Returns required_apps from an app's hooks.py file.
	"""

	with open(hooks_path) as f:
		hooks = f.read()

	for assign in ast.parse(hooks).body:
		if not hasattr(assign, "targets") or not len(assign.targets):
			continue

		if not hasattr(assign.targets[0], "id"):
			continue

		if not assign.targets[0].id == "required_apps":
			continue

		if not isinstance(assign.value, ast.List):
			return []

		return [v.value for v in assign.value.elts]

	return []
