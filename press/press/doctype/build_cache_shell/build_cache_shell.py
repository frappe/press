# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document

from press.agent import Agent


class BuildCacheShell(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		build_server: DF.Link
		cache_target: DF.Data
		command: DF.Code
		cwd: DF.Data | None
		image_tag: DF.Data | None
		output: DF.Code | None
		returncode: DF.Int
	# end: auto-generated types

	def run_command(self):
		frappe.only_for("System Manager")
		result = self._run_command() or {}
		self.output = result.get("output", "# no-output")
		self.cwd = result.get("cwd")
		self.image_tag = result.get("image_tag")
		self.returncode = result.get("returncode")
		frappe.db.commit()

	def _run_command(self):
		if not self.build_server:
			frappe.throw("Please select a <b>Build Server</b>.")

		return Agent(self.build_server).run_command_in_docker_cache(
			self.command,
			self.cache_target,
		)


@frappe.whitelist()
def run_command(doc):
	bench_shell: "BuildCacheShell" = frappe.get_doc(json.loads(doc))
	bench_shell.run_command()
	return bench_shell.as_dict()
