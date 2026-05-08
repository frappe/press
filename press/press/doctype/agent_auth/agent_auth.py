# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import datetime
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.server.server import BaseServer


class AgentAuth(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expires_in: DF.Datetime | None
		is_agent_auth_setup: DF.Check
		public_key: DF.Data | None
		regenerate_public_key: DF.Data | None
		server: DF.Data | None
		server_type: DF.Data | None
	# end: auto-generated types

	def _regenerate_token(self):
		if not self.is_agent_auth_setup:
			return

		# prevent concurrent regeneration
		lock_key = f"agent_auth_regeneration:{self.server}"

		with frappe.cache().lock(lock_key, timeout=600):
			# already rotating
			if self.regenerate_public_key:
				return

			# preserve current public key temporarily
			self.regenerate_public_key = self.public_key

			self.save(ignore_permissions=True)

			# cache old key for dual verification window
			frappe.cache().set_value(
				f"{self.server}_regenerate_public_key",
				self.regenerate_public_key,
				expires_in_sec=300,  # 5 min
			)

			server: BaseServer = frappe.get_doc(
				self.server_type,
				self.server,
			)

			server._setup_agent_auth()


def regenerate_token():
	seven_days_from_now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).replace(
		tzinfo=None
	)

	agent_auths = frappe.get_all(
		"Agent Auth",
		filters={
			"is_agent_auth_setup": 1,
			"expires_in": ["<=", seven_days_from_now],
		},
		fields=["name"],
	)

	for auth in agent_auths:
		frappe.enqueue_doc(
			"Agent Auth",
			auth.name,
			"_regenerate_token",
			queue="long",
			timeout=1200,
		)
