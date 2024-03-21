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


class BenchShellLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		cmd: DF.Code | None
		directory: DF.Data | None
		duration: DF.Float
		end: DF.Datetime | None
		output: DF.Code | None
		returncode: DF.Int
		start: DF.Datetime | None
		status: DF.Data | None
		subdir: DF.Data | None
		traceback: DF.Code | None
	# end: auto-generated types


def create_bench_shell_log(
	res: "ExecuteResult",
	bench: str,
	cmd: str,
	subdir: Optional[str],
	save_output: bool,
) -> None:
	doc_dict = {
		"doctype": "Bench Shell Log",
		"cmd": cmd,
		"bench": bench,
		"subdir": subdir,
		**res,
	}
	doc_dict["start"] = datetime.fromisoformat(res["start"])
	doc_dict["end"] = datetime.fromisoformat(res["end"])
	if not save_output:
		del doc_dict["output"]
	frappe.get_doc(doc_dict).insert()
	frappe.db.commit()
