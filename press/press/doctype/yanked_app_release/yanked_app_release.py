# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class YankedAppRelease(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		hash: DF.Data
		parent_app_release: DF.Link
		team: DF.Link
	# end: auto-generated types

	def after_insert(self):
		"""Ensure that at least this app release is marked as yanked, ignoring other app releases using this commit hash"""
		frappe.db.set_value(
			"App Release",
			{"name": self.parent_app_release},
			{
				"invalid_release": True,
				"invalidation_reason": "Yanked-Release",
				"status": "Yanked",
			},
		)

	def on_trash(self):
		"""Ensure that this app release is marked as Approved since only approved releases are allowed to be yanked"""
		frappe.db.set_value(
			"App Release",
			{"name": self.parent_app_release},
			{"invalid_release": False, "invalidation_reason": "", "status": "Approved"},
		)
