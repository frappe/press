# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""DigitalOcean issues invoices monthly and nothing in between, which is too late to
be an early warning. Droplets carry a real price on the sizes API; block storage and
snapshots do not, so their rates are set on Cloud Cost Settings rather than guessed at
in code.
"""

import frappe
import pydo
from frappe.utils import flt, getdate

from press.press.doctype.cloud_cost_daily.adapters.base import ACCRUED, CostSource

DAYS_PER_MONTH = 30
PAGE_SIZE = 200


class DigitalOceanCostSource(CostSource):
	provider = "DigitalOcean"
	source = ACCRUED
	currency = "USD"

	def fetch(self, start, end):
		cluster = self.get_cluster()
		client = pydo.Client(token=cluster.get_password("digital_ocean_api_token"))
		settings = frappe.get_single("Cloud Cost Settings")

		date = str(getdate())
		rows = [
			*self.price_droplets(client, date, cluster),
			*self.price_volumes(client, date, cluster, flt(settings.do_volume_rate)),
			*self.price_snapshots(client, date, cluster, flt(settings.do_snapshot_rate)),
		]
		return {date: rows}

	def price_droplets(self, client, date, cluster):
		monthly_by_size = {size["slug"]: flt(size["price_monthly"]) for size in self.sizes(client)}

		counts = {}
		for droplet in self.paginate(client.droplets.list, "droplets"):
			region = (droplet.get("region") or {}).get("slug") or cluster.region
			key = (droplet.get("size_slug"), region)
			counts[key] = counts.get(key, 0) + 1

		return [
			self.row(
				date,
				"Droplets",
				f"Droplet:{slug}",
				region,
				count * monthly_by_size.get(slug, 0) / DAYS_PER_MONTH,
				count,
				"Droplet",
			)
			for (slug, region), count in counts.items()
		]

	def price_volumes(self, client, date, cluster, rate):
		size_by_region = {}
		for volume in self.paginate(client.volumes.list, "volumes"):
			region = (volume.get("region") or {}).get("slug") or cluster.region
			size_by_region[region] = size_by_region.get(region, 0) + flt(volume.get("size_gigabytes"))

		return [
			self.row(date, "Block Storage", "Volume", region, size * rate / DAYS_PER_MONTH, size, "GB")
			for region, size in size_by_region.items()
		]

	def price_snapshots(self, client, date, cluster, rate):
		size = sum(
			flt(snapshot.get("size_gigabytes"))
			for snapshot in self.paginate(client.snapshots.list, "snapshots")
		)
		if not size:
			return []

		return [
			self.row(date, "Snapshots", "Snapshot", cluster.region, size * rate / DAYS_PER_MONTH, size, "GB")
		]

	def sizes(self, client):
		return self.paginate(client.sizes.list, "sizes")

	def paginate(self, list_call, key):
		items, page = [], 1
		while True:
			batch = list_call(per_page=PAGE_SIZE, page=page).get(key) or []
			items.extend(batch)
			if len(batch) < PAGE_SIZE:
				return items
			page += 1
