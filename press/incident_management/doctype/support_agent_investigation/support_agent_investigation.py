from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document

from press.access.support_access import has_support_access
from press.incident_management.support_agent.collectors import collect_site_context
from press.incident_management.support_agent.redaction import redact
from press.incident_management.support_agent.report import generate_report
from press.utils import log_error


class SupportAgentInvestigation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		completed_at: DF.Datetime | None
		confidence: DF.Literal["", "Low", "Medium", "High"]
		errors_json: DF.JSON | None
		evidence_json: DF.JSON | None
		failure_reason: DF.SmallText | None
		likely_cause: DF.SmallText | None
		llm_model: DF.Data | None
		payload_json: DF.JSON | None
		recommended_next_steps: DF.Text | None
		redaction_version: DF.Data | None
		requested_by: DF.Link | None
		site: DF.Link
		started_at: DF.Datetime | None
		status: DF.Literal["Queued", "Running", "Completed", "Failed"]
		summary: DF.SmallText | None
		timeline_json: DF.JSON | None
	# end: auto-generated types

	def before_insert(self):
		self.status = self.status or "Queued"
		self.requested_by = self.requested_by or frappe.session.user

	@frappe.whitelist(methods=["POST"])
	def start(self):
		validate_site_access(self.site)
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"run",
			queue="long",
			timeout=900,
			enqueue_after_commit=True,
		)
		return self.name

	def run(self):
		self.status = "Running"
		self.started_at = frappe.utils.now_datetime()
		self.failure_reason = None
		self.save(ignore_permissions=True)
		frappe.db.commit()

		try:
			payload = redact(collect_site_context(self.site))
			report = generate_report(payload)
			self.status = "Completed"
			self.completed_at = frappe.utils.now_datetime()
			self.summary = report["summary"]
			self.likely_cause = report["likely_cause"]
			self.recommended_next_steps = "\n".join(report["recommended_next_steps"])
			self.confidence = report["confidence"]
			self.evidence_json = frappe.as_json(report["evidence"])
			self.timeline_json = frappe.as_json(report["timeline"])
			self.errors_json = frappe.as_json(payload.get("errors", {}))
			self.payload_json = frappe.as_json(payload)
			self.save(ignore_permissions=True)
		except Exception as exc:
			self.status = "Failed"
			self.completed_at = frappe.utils.now_datetime()
			self.failure_reason = redact(str(exc))
			self.save(ignore_permissions=True)
			log_error(
				"Support Agent Investigation Failed",
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
			frappe.db.commit()
			raise


@frappe.whitelist(methods=["POST"])
def create_investigation(site: str, run_now: bool = True) -> str:
	site = validate_site_access(site)
	doc = frappe.get_doc(
		{
			"doctype": "Support Agent Investigation",
			"site": site,
			"status": "Queued",
			"requested_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)

	if run_now:
		doc.start()

	return doc.name


@frappe.whitelist(methods=["GET"])
def get_investigation(name: str) -> dict:
	doc = frappe.get_doc("Support Agent Investigation", name)
	validate_site_access(doc.site)
	return {
		"name": doc.name,
		"site": doc.site,
		"status": doc.status,
		"summary": doc.summary,
		"likely_cause": doc.likely_cause,
		"recommended_next_steps": doc.recommended_next_steps,
		"confidence": doc.confidence,
		"evidence": _loads(doc.evidence_json),
		"timeline": _loads(doc.timeline_json),
		"errors": _loads(doc.errors_json),
		"failure_reason": doc.failure_reason,
		"started_at": doc.started_at,
		"completed_at": doc.completed_at,
	}


def validate_site_access(site: str) -> str:
	site = resolve_site_name(site)
	if not frappe.db.exists("Site", site):
		frappe.throw(_("Site {0} not found").format(site), frappe.DoesNotExistError)

	if frappe.local.system_user() or "System Manager" in frappe.get_roles():
		return site

	if has_support_access("Site", site):
		return site

	frappe.throw(_("Not permitted to investigate this site"), frappe.PermissionError)
	return site


def resolve_site_name(site: str) -> str:
	if frappe.db.exists("Site", site):
		return site

	return frappe.db.get_value("Site Domain", site, "site") or site


def _loads(value):
	if not value:
		return None
	if isinstance(value, dict | list):
		return value
	return json.loads(value)
