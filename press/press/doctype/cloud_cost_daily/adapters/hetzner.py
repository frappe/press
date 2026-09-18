# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Hetzner publishes no billing API, so the daily figure is our own inventory priced
at Hetzner's live rate card. The rates come from the provider (`GET /pricing`), only
the quantities are ours.

Traffic is the reason this adapter earns its keep. Hetzner includes a monthly
allowance per server and charges for the rest, and that overage appears nowhere until
the invoice lands. Every server reports its own outgoing bytes, so the overage can be
priced the moment it starts rather than a month later.
"""

from frappe.utils import flt, getdate
from hcloud import Client as HetznerClient

from press.press.doctype.cloud_cost_daily.adapters.base import ACCRUED, CostSource

BYTES_PER_TB = 1000**4
BYTES_PER_GB = 1024**3
DAYS_PER_MONTH = 30


class HetznerCostSource(CostSource):
	provider = "Hetzner"
	source = ACCRUED
	currency = "EUR"

	def fetch(self, start, end):
		"""Inventory can only be priced as it stands now, so the window is ignored and
		today is the only day answered for."""
		cluster = self.get_cluster()
		client = HetznerClient(token=cluster.get_password("hetzner_api_token"))
		pricing = client.request("GET", "/pricing")["pricing"]
		self.currency = pricing.get("currency") or self.currency

		date = str(getdate())
		rows = [
			*self.price_servers(client, pricing, date),
			*self.price_volumes(client, pricing, date, cluster),
			*self.price_snapshots(client, pricing, date, cluster),
		]
		return {date: rows}

	def price_servers(self, client, pricing, date):
		"""One row per server type per location, plus the traffic those servers ran over
		their included allowance."""
		servers = client.servers.get_all()

		monthly_by_type = {}
		traffic_by_location = {}
		for server in servers:
			location = self.location_of(server)
			price = self.price_for_location(server.server_type.prices, location)
			if price:
				key = (f"Server:{server.server_type.name}", location)
				monthly_by_type[key] = monthly_by_type.get(key, 0) + net(price.get("price_monthly"))

			overage = flt(server.outgoing_traffic) - flt(server.included_traffic)
			if overage > 0 and price:
				rate = net(price.get("price_per_tb_traffic"))
				bucket = traffic_by_location.setdefault(location, {"bytes": 0, "cost": 0})
				bucket["bytes"] += overage
				bucket["cost"] += overage / BYTES_PER_TB * rate

		rows = [
			self.row(date, "Compute", usage_type, location, monthly / DAYS_PER_MONTH, 1, "Server")
			for (usage_type, location), monthly in monthly_by_type.items()
		]
		rows.extend(
			# Traffic is consumed as it happens rather than accrued monthly, so unlike
			# every other row here it is not divided across the month.
			self.row(
				date, "Traffic", "Traffic", location, bucket["cost"], bucket["bytes"] / BYTES_PER_TB, "TB"
			)
			for location, bucket in traffic_by_location.items()
		)
		return rows

	def price_volumes(self, client, pricing, date, cluster):
		rate = net(pricing.get("volume", {}).get("price_per_gb_month"))
		size_by_location = {}
		for volume in client.volumes.get_all():
			location = volume.location.name if volume.location else cluster.region
			size_by_location[location] = size_by_location.get(location, 0) + flt(volume.size)

		return [
			self.row(date, "Block Storage", "Volume", location, size * rate / DAYS_PER_MONTH, size, "GB")
			for location, size in size_by_location.items()
		]

	def price_snapshots(self, client, pricing, date, cluster):
		rate = net(pricing.get("image", {}).get("price_per_gb_month"))
		size = sum(flt(image.image_size) for image in client.images.get_all(type="snapshot"))
		if not size:
			return []

		return [
			self.row(date, "Snapshots", "Snapshot", cluster.region, size * rate / DAYS_PER_MONTH, size, "GB")
		]

	def location_of(self, server):
		if server.datacenter and server.datacenter.location:
			return server.datacenter.location.name
		return ""

	def price_for_location(self, prices, location):
		for price in prices or []:
			if price.get("location") == location:
				return price
		return (prices or [None])[0]


def net(price):
	"""Hetzner quotes both net and gross. Net is what a business pays, and VAT is not
	a cloud cost."""
	if not price:
		return 0
	return flt(price.get("net"))
