"""Random selection of rows, to spread recurring work across many rows."""

import frappe
from frappe.query_builder.functions import Function


def get_random_names(doctype: str, filters=None, limit: int | None = None) -> list[str]:
	"""Return up to `limit` names matching `filters`, in a random order.

	Frappe 16 rejects `RAND()` in `order_by`, so the randomness is a term.
	"""
	query = frappe.qb.get_query(doctype, fields=["name"], filters=filters, limit=limit)
	return [row[0] for row in query.orderby(_RandomOrder()).run()]


class _RandomOrder(Function):
	"""`RAND()` as a query builder term, for MariaDB.

	`Function` renders its own name, so it needs an alias in the clause.
	"""

	def __init__(self):
		super().__init__("RAND")

	def get_sql(self, **kwargs) -> str:
		return "RAND()"
