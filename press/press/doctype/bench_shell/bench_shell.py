# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench


class BenchShell(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		command: DF.Code | None
		directory: DF.Data | None
		duration: DF.Float
		output: DF.Code | None
		returncode: DF.Int
		save_output: DF.Check
		subdir: DF.Data | None
		traceback: DF.Code | None
	# end: auto-generated types

	def run_command(self):
		frappe.only_for("System Manager")

		bench: "Bench" = frappe.get_doc("Bench", self.bench)
		try:
			result = bench.docker_execute(
				self.command,
				self.subdir,
				self.save_output,
			)
		except Exception:
			self.save_output = False
			self.output = None
			self.traceback = frappe.get_traceback()
			return

		self.output = result.get("output")
		self.directory = result.get("directory")
		self.traceback = result.get("traceback")
		self.returncode = result.get("returncode")
		self.duration = result.get("duration")
		frappe.db.commit()


@frappe.whitelist()
def run_command(doc):
	bench_shell: "BenchShell" = frappe.get_doc(json.loads(doc))
	bench_shell.run_command()
	return bench_shell.as_dict()
