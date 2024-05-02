import semantic_version as sv
from typing import TYPE_CHECKING
from press.press.doctype.deploy_candidate.utils import (
	PackageManagers,
	PackageManagerFiles,
)


if TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import (
		DeployCandidate,
	)


class PreBuildValidations:
	dc: "DeployCandidate"
	pmf: PackageManagerFiles

	def __init__(self, dc: "DeployCandidate", pmf: PackageManagerFiles):
		self.dc = dc
		self.pmf = pmf

	def validate(self):
		self._validate_syntax()
		self._validate_node_requirement()
		self._validate_frappe_dependencies()

	def _validate_syntax(self):
		pass

	def _validate_node_requirement(self):
		actual = self.dc.get_dependency_version("node")
		for app, pm in self.pmf.items():
			self._validate_node_version(app, actual, pm)

	def _validate_node_version(self, app: str, actual: str, pm: PackageManagers):
		for pckj in pm["packagejsons"]:
			expected = pckj.get("engines", {}).get("node")
			if expected is None or sv.Version(actual) in sv.SimpleSpec(expected):
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

	def _check_frappe_dependencies(self, app: str, frappe_deps: dict[str, str]):
		for dep_app, actual in frappe_deps.items():
			expected = get_app_version(dep_app)
			if sv.Version(expected) in sv.SimpleSpec(actual):
				continue

			# Do not change args without updating deploy_notifications.py
			raise Exception(
				"Incompatible app version found",
				app,
				dep_app,
				actual,
				expected,
			)


def get_app_version(app: str) -> str:
	# TODO: Complete this
	return "0.0.0"
