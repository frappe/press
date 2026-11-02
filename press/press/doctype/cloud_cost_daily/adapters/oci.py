# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.utils import flt, get_datetime, getdate
from oci.usage_api import UsageapiClient
from oci.usage_api.models import RequestSummarizedUsagesDetails

from press.press.doctype.cloud_cost_daily.adapters.base import BILLED, CostSource

# OCI's Usage API is the direct peer of Cost Explorer: service is the coarse answer,
# the SKU name is the one that separates storing more from computing more.
GROUP_BY = ["service", "skuName", "region"]


class OCICostSource(CostSource):
	provider = "OCI"
	source = BILLED

	def fetch(self, start, end):
		cluster = self.get_cluster()
		config = cluster.get_oci_config()
		client = UsageapiClient(config)

		details = RequestSummarizedUsagesDetails(
			tenant_id=config["tenancy"],
			time_usage_started=get_datetime(str(getdate(start))),
			time_usage_ended=get_datetime(str(getdate(end))),
			granularity="DAILY",
			query_type="COST",
			group_by=GROUP_BY,
		)

		rows_by_date = {}
		page = {}
		while True:
			response = client.request_summarized_usages(details, **page)
			self.collect(response.data.items, rows_by_date)

			if not response.has_next_page:
				return rows_by_date
			page = {"page": response.next_page}

	def collect(self, items, rows_by_date):
		for item in items:
			date = str(getdate(item.time_usage_started))
			row = self.row(
				date,
				item.service or "Unknown",
				item.sku_name or item.sku_part_number or "Unknown",
				item.region,
				flt(item.computed_amount),
				flt(item.computed_quantity),
				item.unit,
			)
			# A tenancy bills in one currency, but the API states it per row and that is
			# the only place we get told which one.
			row["currency"] = item.currency or self.currency
			rows_by_date.setdefault(date, []).append(row)
