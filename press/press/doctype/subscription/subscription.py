# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
import rq
from frappe.model.document import Document
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import cint, flt

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.site_plan.site_plan import SitePlan
from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from frappe.types import DF


class Subscription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		additional_storage: DF.Data | None
		document_name: DF.DynamicLink
		document_type: DF.Link
		enabled: DF.Check
		interval: DF.Literal["Hourly", "Daily", "Monthly"]
		marketplace_app_subscription: DF.Link | None
		plan: DF.DynamicLink
		plan_type: DF.Link
		secret_key: DF.Data | None
		site: DF.Link | None
		team: DF.Link
	# end: auto-generated types

	dashboard_fields = (
		"site",
		"enabled",
		"document_type",
		"document_name",
		"team",
	)

	@staticmethod
	def get_list_query(query, **list_args):
		Subscription = frappe.qb.DocType("Subscription")
		UsageRecord = frappe.qb.DocType("Usage Record")
		Plan = frappe.qb.DocType("Marketplace App Plan")
		price_field = Plan.price_inr if frappe.local.team().currency == "INR" else Plan.price_usd
		filters = list_args.get("filters", {})

		query = (
			frappe.qb.from_(Subscription)
			.join(Plan)
			.on(Subscription.plan == Plan.name)
			.left_join(UsageRecord)
			.on(UsageRecord.subscription == Subscription.name)
			.groupby(Subscription.name)
			.select(
				Subscription.site,
				Subscription.enabled,
				price_field.as_("price"),
				Coalesce(Count(UsageRecord.subscription), 0).as_("active_for"),
			)
			.where(
				(Subscription.document_type == "Marketplace App")
				& (Subscription.document_name == filters["document_name"])
				& (Subscription.site != "")
				& (price_field > 0)
			)
			.limit(list_args["limit"])
			.offset(list_args["start"])
		)

		if filters.get("enabled"):
			enabled = 1 if filters["enabled"] == "Active" else 0
			query = query.where(Subscription.enabled == enabled)

		return query.run(as_dict=True)

	def before_validate(self):
		if not self.secret_key and self.document_type == "Marketplace App":
			self.secret_key = frappe.utils.generate_hash(length=40)
			if not frappe.db.exists("Site Config Key", {"key": f"sk_{self.document_name}"}):
				frappe.get_doc(
					doctype="Site Config Key", internal=True, key=f"sk_{self.document_name}"
				).insert(ignore_permissions=True)

	def validate(self):
		self.validate_duplicate()

	def on_update(self):
		if self.plan_type in ["Server Storage Plan", "Server Snapshot Plan"]:
			return

		doc = self.get_subscribed_document()
		plan_field = doc.meta.get_field("plan")
		if not (plan_field and plan_field.options in ["Site Plan", "Server Plan", "Marketplace App Plan"]):
			return

		if self.enabled and doc.plan != self.plan:
			doc.plan = self.plan
			doc.save()

			if doc.doctype == "Server" and doc.is_unified_server:
				# Update database server plan for sanity in case of unified servers
				frappe.db.set_value("Database Server", doc.database_server, "plan", self.plan)

		if not self.enabled and doc.plan:
			doc.plan = ""
			doc.save()

	def enable(self):
		if self.enabled:
			return
		try:
			self.enabled = True
			self.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Enable Subscription Error")

	def disable(self):
		if not self.enabled:
			return
		try:
			self.enabled = False
			self.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Disable Subscription Error")

	def is_valid_subscription(self, date: DF.Date | None = None) -> bool:
		if not date:
			date = frappe.utils.getdate()

		if frappe.utils.getdate(self.creation) <= date:
			return True

		return False

	@frappe.whitelist()
	def create_usage_record(self, date: DF.Date | None = None):  # noqa: C901
		cannot_charge = not self.can_charge_for_subscription()
		if cannot_charge:
			return None

		if self.is_usage_record_created(date):
			return None

		if not self.is_valid_subscription(date):
			return None

		team = frappe.get_cached_doc("Team", self.team)

		if team.parent_team:
			team = frappe.get_cached_doc("Team", team.parent_team)

		if team.billing_team and team.payment_mode == "Paid By Partner":
			team = frappe.get_cached_doc("Team", team.billing_team)

		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan = frappe.get_cached_doc(self.plan_type, self.plan)

		if self.additional_storage:
			price = plan.price_inr if team.currency == "INR" else plan.price_usd
			price_per_day = price / plan.period  # no rounding off to avoid discrepancies
			amount = flt((price_per_day * cint(self.additional_storage)), 2)

		elif self.plan_type == "Server Snapshot Plan":
			price = plan.price_inr if team.currency == "INR" else plan.price_usd
			price_per_day = price / plan.period  # no rounding off to avoid discrepancies
			amount = flt(
				(
					price_per_day
					* cint(frappe.get_value("Server Snapshot", self.document_name, "total_size_gb"))
				),
				2,
			)
		else:
			amount = plan.get_price_for_interval(self.interval, team.currency)

		if self.plan_type == "Server Plan" and self.document_type == "Server":
			is_primary = frappe.db.get_value("Server", self.document_name, "is_primary")
			if not is_primary:
				return None  # If the server is a secondary application server don't create a usage record

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=team.name,
			document_type=self.document_type,
			document_name=self.document_name,
			plan_type=self.plan_type,
			plan=plan.name,
			amount=amount,
			date=date,
			subscription=self.name,
			interval=self.interval,
			site=(
				self.site
				or frappe.get_value("Marketplace App Subscription", self.marketplace_app_subscription, "site")
			)
			if self.document_type == "Marketplace App"
			else None,
		)
		usage_record.insert()
		usage_record.submit()
		return usage_record

	def can_charge_for_subscription(self):
		doc = self.get_subscribed_document()
		if not doc:
			return False

		if hasattr(doc, "can_charge_for_subscription"):
			return doc.can_charge_for_subscription(self)

		return True

	def is_usage_record_created(self, date=None):
		filters = {
			"team": self.team,
			"document_type": self.document_type,
			"document_name": self.document_name,
			"subscription": self.name,
			"interval": self.interval,
			"plan": self.plan,
		}

		if self.interval == "Daily":
			date = date or frappe.utils.today()
			filters.update({"date": date})

		if self.interval == "Monthly":
			date = frappe.utils.getdate()
			first_day = frappe.utils.get_first_day(date)
			last_day = frappe.utils.get_last_day(date)
			filters.update({"date": ("between", (first_day, last_day))})

		result = frappe.db.get_all("Usage Record", filters=filters, limit=1)
		return bool(result)

	def validate_duplicate(self):
		if not self.is_new():
			return
		filters = {
			"team": self.team,
			"document_type": self.document_type,
			"document_name": self.document_name,
			"plan_type": self.plan_type,
		}
		if self.document_type == "Marketplace App":
			filters.update({"marketplace_app_subscription": self.marketplace_app_subscription})

		results = frappe.db.get_all(
			"Subscription",
			filters,
			pluck="name",
			limit=1,
			ignore_ifnull=True,
		)
		if results:
			link = frappe.utils.get_link_to_form("Subscription", results[0])
			frappe.throw(f"A Subscription already exists: {link}", frappe.DuplicateEntryError)

	def get_subscribed_document(self):
		if not hasattr(self, "_subscribed_document"):
			self._subscribed_document = frappe.get_doc(self.document_type, self.document_name)
		return self._subscribed_document

	@classmethod
	def get_sites_without_offsite_backups(cls) -> list[str]:
		plans = SitePlan.get_ones_without_offsite_backups()
		return frappe.get_all(
			"Subscription",
			filters={"document_type": "Site", "plan": ("in", plans)},
			pluck="document_name",
		)


def create_usage_records():
	create_usage_records_of_date()


def create_usage_records_of_date(
	date: DF.Date | None = None, usage_record_creation_batch_size: int | None = None
):
	"""
	Creates daily usage records for paid Subscriptions

	If no date is provided, it defaults to today.
	If usage_record_creation_batch_size is not provided, it will fetch from `Press Settings` or default to 500.
	"""
	free_sites = sites_with_free_hosting()
	settings = frappe.get_single("Press Settings")
	subscriptions = frappe.db.get_all(
		"Subscription",
		filters={
			"enabled": True,
			"plan": ("in", paid_plans()),
			"name": ("not in", created_usage_records(free_sites, date=date)),
			"document_name": ("not in", free_sites),
		},
		pluck="name",
		order_by=None,
		limit=usage_record_creation_batch_size or settings.usage_record_creation_batch_size or 500,
		ignore_ifnull=True,
		debug=True,
	)
	for name in subscriptions:
		if has_job_timeout_exceeded():
			return
		subscription = frappe.get_cached_doc("Subscription", name)
		try:
			subscription.create_usage_record(date=date)
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			# This job took too long to execute
			# We need to rollback the transaction
			# Try again in the next job
			frappe.db.rollback()
			return
		except Exception:
			frappe.db.rollback()
			log_error(title="Create Usage Record Error", name=name)


def paid_plans():
	paid_plans = []

	doctypes = [
		"Site Plan",
		"Marketplace App Plan",
		"Server Plan",
		"Server Storage Plan",
		"Cluster Plan",
	]

	for name in doctypes:
		doctype = frappe.qb.DocType(name)
		if name in ("Server Plan", "Site Plan"):
			paid_plans += (
				frappe.qb.from_(doctype)
				.select(doctype.name)
				.where(doctype.price_inr > 0)
				.where((doctype.enabled == 1) | (doctype.legacy_plan == 1))
				.run(pluck=True)
			)
		else:
			paid_plans += (
				frappe.qb.from_(doctype)
				.select(doctype.name)
				.where(doctype.price_inr > 0)
				.where(doctype.enabled == 1)
				.run(pluck=True)
			)

	return list(set(paid_plans))


def sites_with_free_hosting():
	# sites marked as free
	free_teams = frappe.get_all("Team", filters={"free_account": True, "enabled": True}, pluck="name")
	free_team_sites = frappe.get_all(
		"Site",
		{"status": ("not in", ("Archived", "Suspended")), "team": ("in", free_teams)},
		pluck="name",
		ignore_ifnull=True,
	)
	return free_team_sites + frappe.get_all(
		"Site",
		filters={
			"free": True,
			"status": ("not in", ("Archived", "Suspended")),
			"team": ("not in", free_teams),
		},
		pluck="name",
		ignore_ifnull=True,
	)


def created_usage_records(free_sites, date=None):
	date = date or frappe.utils.today()
	"""Returns created usage records for a particular date"""
	return frappe.get_all(
		"Usage Record",
		filters={
			"document_type": (
				"in",
				(
					"Site",
					"Server",
					"Database Server",
					"Self Hosted Server",
					"Marketplace App",
					"Cluster",
				),
			),
			"date": date,
			"document_name": ("not in", free_sites),
		},
		pluck="subscription",
		order_by=None,
		ignore_ifnull=True,
	)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Subscription")
