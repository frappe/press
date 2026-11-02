# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, get_datetime_str, getdate, now_datetime

from press.press.doctype.cloud_cost_daily.adapters import ACCRUED, get_source

STORED_FIELDS = [
	"name",
	"creation",
	"modified",
	"owner",
	"modified_by",
	"date",
	"account",
	"provider",
	"source",
	"currency",
	"service",
	"usage_type",
	"region",
	"amortized_cost",
	"unblended_cost",
	"usage_quantity",
	"usage_unit",
]


class CloudCostDaily(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Data
		amortized_cost: DF.Currency
		currency: DF.Link | None
		date: DF.Date
		provider: DF.Literal["AWS EC2", "OCI", "Hetzner", "DigitalOcean"]
		region: DF.Data | None
		service: DF.Data
		source: DF.Literal["Billed", "Accrued"]
		unblended_cost: DF.Currency
		usage_quantity: DF.Float
		usage_type: DF.Data | None
		usage_unit: DF.Data | None
	# end: auto-generated types

	pass


def get_cost_accounts():
	"""The accounts to pull from, worked out from what Press already knows.

	AWS is one account: the payer whose keys are in Press Settings. Per-cluster AWS keys
	are for running machines, not for reading bills, and querying a member account that
	the payer already covers would count its spend twice.

	The other three keep their credentials per cluster because that is where the token
	lives, so each distinct tenancy or project is its own account.
	"""
	accounts = []
	if frappe.db.get_single_value("Press Settings", "aws_access_key_id"):
		accounts.append({"label": "aws", "provider": "AWS EC2", "cluster": None})

	seen = set()
	clusters = frappe.get_all(
		"Cluster",
		{"cloud_provider": ("in", ["OCI", "Hetzner", "DigitalOcean"]), "status": ("!=", "Archived")},
		["name", "cloud_provider", "oci_tenancy"],
		order_by="name asc",
	)
	for cluster in clusters:
		# One OCI tenancy can back several clusters and bills as a whole.
		key = (cluster.cloud_provider, cluster.oci_tenancy or cluster.name)
		if key in seen:
			continue
		seen.add(key)
		accounts.append({"label": cluster.name, "provider": cluster.cloud_provider, "cluster": cluster.name})
	return accounts


def store_rows(label, rows_by_date):
	"""Replace each day wholesale. Providers revise recent days and accrued figures are
	re-priced every run, and a day is small enough that replacing it is simpler and
	safer than diffing every line against what we hold."""
	timestamp = get_datetime_str(now_datetime())
	user = frappe.session.user

	stored = 0
	for date, rows in rows_by_date.items():
		frappe.db.delete("Cloud Cost Daily", {"account": label, "date": date})
		if not rows:
			continue

		values = [
			(
				frappe.generate_hash(length=10),
				timestamp,
				timestamp,
				user,
				user,
				row["date"],
				row["account"],
				row["provider"],
				row["source"],
				row["currency"],
				row["service"],
				row["usage_type"],
				row["region"],
				row["amortized_cost"],
				row["unblended_cost"],
				row["usage_quantity"],
				row["usage_unit"],
			)
			for row in rows
		]
		frappe.db.bulk_insert("Cloud Cost Daily", STORED_FIELDS, values)
		stored += len(values)
	return stored


def ingest_account(account, start, end):
	source = get_source(account)
	return store_rows(account["label"], source.fetch(start, end))


def ingest_daily_costs(start=None, end=None):
	"""Pull the trailing window for every configured account. The window reaches back
	past yesterday because metered providers keep revising recent days; providers with
	no cost API ignore it and price today's inventory instead."""
	settings = frappe.get_single("Cloud Cost Settings")
	end = getdate(end) if end else add_days(getdate(), 1)
	start = getdate(start) if start else add_days(end, -(cint(settings.restatement_days) or 5))

	for account in get_cost_accounts():
		try:
			ingest_account(account, start, end)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title="Cloud Cost Ingest Failed",
				message=f"Account {account['label']} ({account['provider']}) between {start} and {end}",
			)


def backfill_history():
	"""Load the history the metered providers still hold, one month per request so no
	single response has to be paginated far. Accrued providers have no history to
	recover — their series starts the day collection starts."""
	settings = frappe.get_single("Cloud Cost Settings")
	months = cint(settings.backfill_months) or 14

	end = add_days(getdate(), 1)
	for month in range(months):
		window_end = add_months(end, -month)
		window_start = add_months(end, -(month + 1))
		for account in get_cost_accounts():
			if get_source(account).source == ACCRUED:
				continue
			try:
				ingest_account(account, window_start, window_end)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title="Cloud Cost Backfill Failed", message=account["label"])


def purge_old_rows():
	settings = frappe.get_single("Cloud Cost Settings")
	retention_days = cint(settings.retention_days)
	if not retention_days:
		return

	frappe.db.delete("Cloud Cost Daily", {"date": ("<", add_days(getdate(), -retention_days))})
