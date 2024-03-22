# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AnsibleConsoleLog(Document):
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
		output: DF.Table[AnsibleConsoleOutput]
	# end: auto-generated types

	pass
