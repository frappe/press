# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import datetime
from typing import Optional, TypedDict

import frappe
import frappe.utils
import json
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from pypika import Order

# DocType: groupby
RECORD_FOR: dict[str, str] = {
	"Error Log": "method",
}

Counts = TypedDict(
	"Counts",
	{
		"counts": dict[str, int],
		"date": datetime.date,
		"total": int,
	},
)


class LogCounter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		counts: DF.JSON
		date: DF.Date
		groupby: DF.Data
		logtype: DF.Link
		total: DF.Int
	# end: auto-generated types

	def autoname(self):
		self.name = get_name(self.logtype, self.date)


def record_counts():
	date = frappe.utils.now_datetime().date() - datetime.timedelta(days=1)
	for doctype, groupby in RECORD_FOR.items():
		record_for_date(doctype, groupby, date)
	frappe.db.commit()


def record_for_date(
	doctype: str = "Error Log",
	groupby: str = "method",
	date: Optional[datetime.date] = None,
):
	counts = get_counts(
		doctype,
		groupby,
		date,
	)
	name = get_name(doctype, counts["date"])
	counts_json = json.dumps(counts["counts"], indent=2)

	# Update counts if name value exists
	if frappe.db.exists("Log Counter", name):
		frappe.db.set_value("Log Counter", name, "counts", counts_json)
		frappe.db.set_value("Log Counter", name, "total", counts["total"])
		return

	lc = frappe.get_doc(
		{
			"doctype": "Log Counter",
			"logtype": doctype,
			"groupby": groupby,
			"counts": counts_json,
			"total": counts["total"],
			"date": counts["date"],
		}
	)
	lc.insert()


def get_counts(
	doctype: str = "Error Log",
	groupby: str = "method",
	date: Optional[datetime.date] = None,
) -> Counts:
	date_to = date if date else frappe.utils.now_datetime().date()
	date_from = date_to - datetime.timedelta(days=1)

	table = DocType(doctype)
	column = table[groupby]

	q = frappe.qb.from_(table)
	q = q.select(column, Count("*", alias="count"))
	q = q.where(table.creation[date_from:date_to])
	q = q.groupby(column)
	q = q.orderby("count", order=Order.desc)
	r = q.run()

	counts = {c[0]: c[1] for c in r}
	total = sum(c[1] for c in r)
	return dict(counts=counts, date=date_to, total=total)


def get_name(doctype: str, date: datetime.date):
	dt_stub = doctype.lower().replace(" ", "_")
	date_iso = date.isoformat().replace("-", "_")
	return f"{dt_stub}-{date_iso}"
