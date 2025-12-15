# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe.model.document import Document

from press.runner import AnsibleAdHoc


class AnsibleConsole(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.ansible_console_output.ansible_console_output import (
			AnsibleConsoleOutput,
		)

		command: DF.Code | None
		error: DF.Code | None
		inventory: DF.Code | None
		nonce: DF.Data | None
		output: DF.Table[AnsibleConsoleOutput]
	# end: auto-generated types

	def run(self):
		frappe.only_for("System Manager")
		if not self.command:
			frappe.throw("Command is required")
			return

		def _on_publish(nonce, output):
			frappe.publish_realtime(
				event="ansible_console_update",
				doctype="Ansible Console",
				docname="Ansible Console",
				user=frappe.session.user,
				message={
					"nonce": nonce,
					"output": output,
				},
			)

		try:
			ad_hoc = AnsibleAdHoc(self.inventory or "", self.nonce, on_publish=_on_publish)
			for host in ad_hoc.run(self.command):
				self.append("output", host)
		except Exception:
			self.error = frappe.get_traceback()
			import traceback

			traceback.print_exc()
		log = self.as_dict()
		log.update({"doctype": "Ansible Console Log"})
		frappe.get_doc(log).insert()
		frappe.db.commit()


@frappe.whitelist()
def execute_command(doc):
	frappe.enqueue(
		"press.press.doctype.ansible_console.ansible_console._execute_command",
		doc=doc,
		timeout=7200,
	)
	return doc


def _execute_command(doc):
	console = frappe.get_doc(json.loads(doc))
	console.run()
	return console.as_dict()
