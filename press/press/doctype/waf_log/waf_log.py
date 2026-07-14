# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document


class WAFLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal["Intercepted", "Passed"]
		client_ip: DF.Data | None
		matched_data: DF.SmallText | None
		raw_log: DF.Code | None
		request_method: DF.Data | None
		request_uri: DF.SmallText | None
		rule_id: DF.Data | None
		rule_msg: DF.SmallText | None
		server: DF.Link | None
		severity: DF.Literal["CRITICAL", "ERROR", "WARNING", "NOTICE", "INFO", "DEBUG"]
		site: DF.Link
		timestamp: DF.Datetime
		transaction_id: DF.Data
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days: int = 14) -> None:
		"""Delete WAF Log rows older than the given number of days.

		Mirrors `AlertmanagerWebhookLog.clear_old_logs` so it can be wired into
		the existing log retention scheduler.
		"""
		_clear_old_logs(days)


def clear_old_logs(days: int = 14) -> None:
	"""Module-level entrypoint for the daily scheduler.

	WAF Log retention — wired in `press/hooks.py:scheduler_events["daily"]`.
	The scheduler only resolves module-level callables, so this thin wrapper
	dispatches to the static helper on the Doctype (mirroring the pattern used
	by `AlertmanagerWebhookLog`).
	"""
	_clear_old_logs(days)


def _clear_old_logs(days: int = 14) -> None:
	from frappe.query_builder import Interval
	from frappe.query_builder.functions import Now

	table = frappe.qb.DocType("WAF Log")
	frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))
