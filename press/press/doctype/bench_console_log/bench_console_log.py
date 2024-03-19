# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime
from typing import Optional, TypedDict

import frappe
from frappe.model.document import Document

ExecuteResult = TypedDict(
	"ExecuteResult",
	{
		"command": str,
		"status": str,
		"start": str,
		"end": str,
		"duration": float,
		"output": str,
		"directory": Optional[str],
		"traceback": Optional[str],
		"returncode": Optional[int],
	},
)


class BenchConsoleLog(Document):
	pass


def create_bench_console_log(
	res: "ExecuteResult", bench: str, cmd: str, subdir: Optional[str]
) -> None:
	doc_dict = {
		"doctype": "Bench Console Log",
		"cmd": cmd,
		"bench": bench,
		"subdir": subdir,
		**res,
	}
	doc_dict["start"] = datetime.fromisoformat(res["start"])
	doc_dict["end"] = datetime.fromisoformat(res["end"])
	frappe.get_doc(doc_dict).insert()
	frappe.db.commit()
