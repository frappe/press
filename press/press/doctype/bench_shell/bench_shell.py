# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from press.access.actions import ReleaseGroupActions
from press.access.support_access import can_perform

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench

ALLOWED_ROLES = ["System Manager", "Press Support Engineer"]


class BenchShell(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		as_root: DF.Check
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
		self.check_permission_to_run()

		bench: "Bench" = frappe.get_doc("Bench", self.bench)
		try:
			result = bench.docker_execute(self.command, self.subdir, self.save_output, as_root=self.as_root)
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

	def check_permission_to_run(self):
		"""Staff without System Manager run as the bench user, and need the consent of the team."""
		frappe.only_for(ALLOWED_ROLES, message=True)
		if "System Manager" in frappe.get_roles():
			return
		if self.as_root:
			frappe.throw(_("Only a System Manager can run a command as root"), frappe.PermissionError)
		self.check_team_consent()

	def check_team_consent(self):
		group = cstr(frappe.db.get_value("Bench", self.bench, "group"))
		team, public = frappe.db.get_value("Release Group", group, ["team", "public"]) or (None, 1)
		# A public group counts as granted in every grant check, so refuse it first
		if public:
			frappe.throw(
				_("Public bench groups need a System Manager. {0} is public.").format(group),
				frappe.PermissionError,
			)
		if not can_perform("Release Group", group, cstr(team), ReleaseGroupActions.SSHAccess.value):
			frappe.throw(
				_(
					"Request Support Access with SSH on the bench group {0} to run commands on its benches"
				).format(group),
				frappe.PermissionError,
			)


@frappe.whitelist()
def run_command(doc):
	# The DocType is fixed, so a crafted document cannot run the method of another console.
	bench_shell = BenchShell({**json.loads(doc), "doctype": "Bench Shell"})
	bench_shell.run_command()
	return bench_shell.as_dict()
