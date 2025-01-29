# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class SSHAccessAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.ssh_access_audit_command.ssh_access_audit_command import (
			SSHAccessAuditCommand,
		)
		from press.infrastructure.doctype.ssh_access_audit_violation.ssh_access_audit_violation import (
			SSHAccessAuditViolation,
		)

		commands: DF.Table[SSHAccessAuditCommand]
		inventory: DF.Code | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		violations: DF.Table[SSHAccessAuditViolation]
	# end: auto-generated types

	pass



