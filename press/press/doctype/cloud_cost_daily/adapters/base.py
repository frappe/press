# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""One shape for four providers that answer the cost question very differently.

AWS and OCI both meter: ask them what a day cost and they answer per service and
per usage type. Hetzner has no billing API at all, and DigitalOcean has only monthly
invoices, so for those two the only daily number available is our own inventory priced
at the provider's published rates.

Both kinds land in the same table and feed the same detectors, but they are marked
apart. An accrued figure is a model of the bill, not the bill, and reading one as the
other is how a cost system starts lying.
"""

import frappe

BILLED = "Billed"
ACCRUED = "Accrued"


class CostSource:
	"""A provider's daily cost and usage, however it has to be obtained."""

	provider = ""
	source = BILLED
	currency = "USD"

	def __init__(self, account):
		self.account = account
		self.label = account["label"]
		self.cluster = account.get("cluster")

	def fetch(self, start, end):
		"""Rows keyed by day. Accrued sources can only answer for today, so they return
		one day however wide the window is."""
		raise NotImplementedError

	def row(self, date, service, usage_type, region, cost, quantity=0, unit=None):
		return {
			"date": str(date),
			"account": self.label,
			"provider": self.provider,
			"source": self.source,
			"currency": self.currency,
			"service": service,
			"usage_type": usage_type,
			"region": region or "",
			"amortized_cost": cost,
			"unblended_cost": cost,
			"usage_quantity": quantity,
			"usage_unit": unit,
		}

	def get_cluster(self):
		if not self.cluster:
			frappe.throw(f"{self.provider} account {self.label} needs a cluster to read credentials from")
		return frappe.get_doc("Cluster", self.cluster)


def get_source(account):
	from press.press.doctype.cloud_cost_daily.adapters.aws import AWSCostSource
	from press.press.doctype.cloud_cost_daily.adapters.digitalocean import DigitalOceanCostSource
	from press.press.doctype.cloud_cost_daily.adapters.hetzner import HetznerCostSource
	from press.press.doctype.cloud_cost_daily.adapters.oci import OCICostSource

	sources = {
		source.provider: source
		for source in (AWSCostSource, OCICostSource, HetznerCostSource, DigitalOceanCostSource)
	}
	provider = account.get("provider") or "AWS EC2"
	if provider not in sources:
		frappe.throw(f"No cost source is implemented for {provider}")
	return sources[provider](account)
