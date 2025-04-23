# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class AgentUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.agent_update_server.agent_update_server import AgentUpdateServer

		app_server: DF.Check
		auto_rollback_changes: DF.Check
		branch: DF.Data | None
		commit_hash: DF.Data | None
		database_server: DF.Check
		end: DF.Datetime | None
		exclude_self_hosted_servers: DF.Check
		proxy_server: DF.Check
		repo: DF.Data | None
		restart_background_workers: DF.Check
		restart_redis: DF.Check
		restart_web_workers: DF.Check
		rollback_commit: DF.Data | None
		servers: DF.Table[AgentUpdateServer]
		start: DF.Datetime | None
		status: DF.Literal["Draft", "Running", "Rollbacking", "Success", "Failure"]
	# end: auto-generated types

	def validate(self):
		pass

	def before_insert(self):
		self.status = "Draft"
		press_settings = frappe.get_single("Press Settings")
		repository_owner = press_settings.agent_repository_owner or "frappe"
		self.repo = f"github.com/{repository_owner}/agent"
		self.branch = press_settings.branch or "master"

