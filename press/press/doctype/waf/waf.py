# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

if TYPE_CHECKING:
	from frappe.types import DF

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.server.server import Server
	from press.press.doctype.site.site import Site
	from press.press.doctype.waf_blocked_endpoint.waf_blocked_endpoint import WAFBlockedEndpoint
	from press.press.doctype.waf_blocked_parameter.waf_blocked_parameter import WAFBlockedParameter
	from press.press.doctype.waf_custom_rule.waf_custom_rule import WAFCustomRule
	from press.press.doctype.waf_ip_rule.waf_ip_rule import WAFIPRule
	from press.press.doctype.waf_rate_limit.waf_rate_limit import WAFRateLimit
	from press.press.doctype.waf_request_limit.waf_request_limit import WAFRequestLimit


class WAF(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.waf_blocked_endpoint.waf_blocked_endpoint import WAFBlockedEndpoint
		from press.press.doctype.waf_blocked_parameter.waf_blocked_parameter import WAFBlockedParameter
		from press.press.doctype.waf_custom_rule.waf_custom_rule import WAFCustomRule
		from press.press.doctype.waf_ip_rule.waf_ip_rule import WAFIPRule
		from press.press.doctype.waf_rate_limit.waf_rate_limit import WAFRateLimit
		from press.press.doctype.waf_request_limit.waf_request_limit import WAFRequestLimit

		blocked_endpoints: DF.Table[WAFBlockedEndpoint]
		blocked_parameters: DF.Table[WAFBlockedParameter]
		custom_rules: DF.Table[WAFCustomRule]
		enabled: DF.Check
		ip_rules: DF.Table[WAFIPRule]
		last_synced: DF.Datetime | None
		mode: DF.Literal["", "Detection", "Prevention"]
		rate_limits: DF.Table[WAFRateLimit]
		request_limits: DF.Table[WAFRequestLimit]
		site: DF.Link
		waf_log_token: DF.Password
	# end: auto-generated types

	def validate(self) -> None:
		self.validate_custom_rule_ids()

	def on_update(self) -> None:
		"""Trigger an Agent job to push the new WAF config to the site's server.

		Lazy-import to avoid circulars with press.agent at module import time
		(matches the pattern used by Site.on_update). Skipped when the save
		originated from token rotation (which only mutates `waf_log_token` and
		dispatches its own dedicated `Rotate WAF Log Token` job).

		Agent-sync failures are caught and logged so saving a WAF doc never
		crashes — the WAF DocType is the source of truth and the agent push
		is a best-effort side effect (mirrors `Site.archive_waf`). This is
		important during development when Agent Job Type fixtures may not yet
		be synced into the DB.
		"""
		if frappe.flags.in_test or frappe.flags.in_patch:
			return
		site: Site = frappe.get_doc("Site", self.site)
		server: Server = frappe.get_doc("Server", site.server)
		if server.is_waf_setup is False:
			frappe.throw(
				"Cannot sync WAF config to Agent: WAF is not yet setup on the server. Setup WAF on the server first, then try again."
			)
		if self.flags.skip_agent_sync:
			return
		try:
			self.enqueue_apply_to_agent()
		except Exception:
			from press.utils import log_error

			log_error("WAF Agent sync failed", site=self.site, waf=self.name)

	def validate_custom_rule_ids(self) -> None:
		seen: set[int] = set()
		for row in self.custom_rules:
			if row.rule_id in seen:
				frappe.throw(_("Custom WAF rule id {0} is duplicated.").format(row.rule_id))
			seen.add(row.rule_id)

	# ------------------------------------------------------------------
	# Lifecycle / Agent integration
	# ------------------------------------------------------------------

	def get_log_token(self) -> str:
		"""Return the cleartext WAF log token for this site."""
		if not self.waf_log_token:
			self.flags.skip_agent_sync = True
			self.waf_log_token = frappe.generate_hash(length=40)
			self.save(ignore_permissions=True)
		return get_decrypted_password(self.doctype, self.name, "waf_log_token")

	def rotate_log_token(self) -> str:
		"""Generate a fresh log token and persist it."""
		self.flags.skip_agent_sync = True
		self.waf_log_token = frappe.generate_hash(length=40)
		self.save(ignore_permissions=True)
		return self.get_log_token()

	def enqueue_apply_to_agent(self) -> None:
		"""Push this configuration to the Agent owning the site's bench."""

		if not self.enabled:
			self._sync_agent_job("disable")
			return
		self._sync_agent_job("update")

	def _site_server(self) -> str:
		return frappe.db.get_value("Site", self.site, "server")

	# Convenience accessors consumed by `press.agent.Agent` so the AgentJob
	# `request_data` is fully self-describing without Press-side round-trips.
	@property
	def site_name(self) -> str:
		return self.site

	@property
	def site_bench(self) -> str | None:
		return frappe.db.get_value("Site", self.site, "bench")

	def _sync_agent_job(self, action: str) -> None:
		from press.agent import Agent

		server = self._site_server()
		if not server:
			return  # Site not yet assigned to a server; nothing to push.
		agent = Agent(server)
		if action == "update":
			agent.update_waf_config(self)
		elif action == "disable":
			agent.disable_waf(self)
		elif action == "rotate_token":
			agent.rotate_waf_log_token(self)


# ----------------------------------------------------------------------
# AgentJob callback (dispatched from AgentJob.process_job_updates)
# ----------------------------------------------------------------------


def process_waf_job_update(job: "AgentJob") -> None:
	"""Handle completion of a WAF-related AgentJob.

	Mirrors the per-doctype `process_*_job_update` functions registered in
	`press.press.doctype.agent_job.agent_job.process_job_updates`. Updates
	`last_synced` on success so the WAF list view can show staleness at a
	glance; logs failures without raising (job lifecycle already logs).
	"""
	if not job.site:
		return
	try:
		waf_name = frappe.db.get_value("WAF", {"site": job.site}, "name")
	except Exception:
		return
	if not waf_name:
		return
	if job.status == "Success":
		frappe.db.set_value("WAF", waf_name, "last_synced", frappe.utils.now_datetime())
	elif job.status == "Failure":
		from press.utils import log_error

		log_error(
			"WAF AgentJob Failed",
			job=job.name,
			job_type=job.job_type,
			site=job.site,
			traceback=getattr(job, "traceback", None),
		)
