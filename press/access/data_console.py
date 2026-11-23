"""System Console for the Press Infrastructure Manager role: read-only SQL, without System Manager."""

import frappe
from frappe import _
from frappe.database.database import get_query_execution_timeout
from frappe.desk.doctype.system_console.system_console import SystemConsole
from frappe.utils.safe_exec import read_sql

from press.access.sql_guard import check_read_only_query

DATA_CONSOLE_ROLE = "Press Infrastructure Manager"
STATEMENT_TIMEOUT = 30
MAX_ROWS = 1000


class PressSystemConsole(SystemConsole):
	def run(self):
		roles = frappe.get_roles()
		if frappe.session.user == "Administrator" or "System Manager" in roles:
			super().run()
			return
		if DATA_CONSOLE_ROLE not in roles:
			frappe.throw(
				_("You need the System Manager role to use the System Console"), frappe.PermissionError
			)
		if self.type != "SQL":
			frappe.throw(_("The {0} role can run SQL only").format(DATA_CONSOLE_ROLE), frappe.PermissionError)
		self.run_read_only_sql()

	def run_read_only_sql(self):
		"""Run the query, then roll back. A refused query is logged too, and its error is raised."""
		self.commit = False
		try:
			check_read_only_query(self.console or "")
			self.output = format_rows(read_with_timeout(self.console or ""))
		except frappe.PermissionError:
			raise
		except Exception:
			self.output = frappe.get_traceback()
		finally:
			frappe.db.rollback()
			self.log()

	def log(self):
		# The audit row must exist even though the role cannot create Console Logs
		log = {"doctype": "Console Log", "script": self.console, "type": self.type, "committed": 0}
		frappe.get_doc(log).insert(ignore_permissions=True)
		frappe.db.commit()


def read_with_timeout(query: str) -> list:
	frappe.db.set_execution_timeout(STATEMENT_TIMEOUT)
	try:
		return list(read_sql(query, as_dict=1) or [])
	finally:
		frappe.db.set_execution_timeout(get_query_execution_timeout())


def format_rows(rows: list) -> str:
	output = frappe.as_json(rows[:MAX_ROWS])  # pyright: ignore[reportArgumentType]
	if len(rows) > MAX_ROWS:
		output += "\n\n" + _("Showing the first {0} of {1} rows").format(MAX_ROWS, len(rows))
	return output
