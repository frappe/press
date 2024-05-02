from typing import TYPE_CHECKING
from press.press.doctype.deploy_candidate.utils import (
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
		pass

	def _validate_frappe_dependencies(self):
		pass
