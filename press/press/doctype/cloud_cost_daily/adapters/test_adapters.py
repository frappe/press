# Copyright (c) 2026, Frappe and Contributors
# See license.txt

"""The adapters are where four providers stop looking alike, so they are tested against
recorded response shapes rather than against a live account."""

from datetime import datetime

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cloud_cost_daily.adapters.digitalocean import DigitalOceanCostSource
from press.press.doctype.cloud_cost_daily.adapters.hetzner import BYTES_PER_TB, HetznerCostSource
from press.press.doctype.cloud_cost_daily.adapters.oci import OCICostSource

DATE = "2026-08-01"


class Bag:
	"""An attribute bag standing in for a provider SDK object."""

	def __init__(self, **fields):
		self.__dict__.update(fields)

	def get_all(self, **_kwargs):
		return self.items

	def list(self, **_kwargs):
		return self.page


def hetzner_source():
	return HetznerCostSource({"label": "hel", "provider": "Hetzner", "cluster": "fsn1"})


def hetzner_pricing():
	return {
		"currency": "EUR",
		"volume": {"price_per_gb_month": {"net": "0.0400", "gross": "0.0476"}},
		"image": {"price_per_gb_month": {"net": "0.0119", "gross": "0.0142"}},
	}


def hetzner_server(outgoing_traffic, included_traffic):
	return Bag(
		server_type=Bag(
			name="cx42",
			prices=[
				{
					"location": "fsn1",
					"price_monthly": {"net": "20.00", "gross": "23.80"},
					"price_per_tb_traffic": {"net": "1.19", "gross": "1.42"},
				}
			],
		),
		datacenter=Bag(location=Bag(name="fsn1")),
		outgoing_traffic=outgoing_traffic,
		included_traffic=included_traffic,
	)


class TestHetznerCostSource(FrappeTestCase):
	def test_monthly_server_price_is_spread_across_the_month(self):
		client = Bag(servers=Bag(items=[hetzner_server(0, BYTES_PER_TB)]))

		rows = hetzner_source().price_servers(client, hetzner_pricing(), DATE)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["usage_type"], "Server:cx42")
		self.assertEqual(rows[0]["region"], "fsn1")
		self.assertAlmostEqual(rows[0]["amortized_cost"], 20 / 30)

	def test_net_price_is_used_because_vat_is_not_a_cloud_cost(self):
		client = Bag(servers=Bag(items=[hetzner_server(0, BYTES_PER_TB)]))

		rows = hetzner_source().price_servers(client, hetzner_pricing(), DATE)

		self.assertNotAlmostEqual(rows[0]["amortized_cost"], 23.80 / 30)

	def test_traffic_over_the_allowance_is_priced_the_day_it_happens(self):
		"""The overage Hetzner shows nowhere until the invoice. It is charged as it is
		used, so unlike the servers it is not divided across the month."""
		client = Bag(servers=Bag(items=[hetzner_server(3 * BYTES_PER_TB, BYTES_PER_TB)]))

		rows = hetzner_source().price_servers(client, hetzner_pricing(), DATE)
		traffic = next(row for row in rows if row["usage_type"] == "Traffic")

		self.assertAlmostEqual(traffic["usage_quantity"], 2)
		self.assertAlmostEqual(traffic["amortized_cost"], 2 * 1.19)

	def test_traffic_within_the_allowance_is_not_charged(self):
		client = Bag(servers=Bag(items=[hetzner_server(BYTES_PER_TB // 2, BYTES_PER_TB)]))

		rows = hetzner_source().price_servers(client, hetzner_pricing(), DATE)

		self.assertEqual([row["usage_type"] for row in rows], ["Server:cx42"])

	def test_identical_servers_are_summed_into_one_row(self):
		client = Bag(servers=Bag(items=[hetzner_server(0, BYTES_PER_TB)] * 3))

		rows = hetzner_source().price_servers(client, hetzner_pricing(), DATE)

		self.assertEqual(len(rows), 1)
		self.assertAlmostEqual(rows[0]["amortized_cost"], 3 * 20 / 30)

	def test_volumes_are_priced_from_the_live_rate_card(self):
		client = Bag(volumes=Bag(items=[Bag(size=100, location=Bag(name="fsn1"))]))
		cluster = Bag(region="fsn1")

		rows = hetzner_source().price_volumes(client, hetzner_pricing(), DATE, cluster)

		self.assertEqual(rows[0]["usage_type"], "Volume")
		self.assertAlmostEqual(rows[0]["usage_quantity"], 100)
		self.assertAlmostEqual(rows[0]["amortized_cost"], 100 * 0.04 / 30)

	def test_snapshots_are_priced_from_the_live_rate_card(self):
		client = Bag(images=Bag(items=[Bag(image_size=50), Bag(image_size=30)]))
		cluster = Bag(region="fsn1")

		rows = hetzner_source().price_snapshots(client, hetzner_pricing(), DATE, cluster)

		self.assertAlmostEqual(rows[0]["usage_quantity"], 80)
		self.assertAlmostEqual(rows[0]["amortized_cost"], 80 * 0.0119 / 30)

	def test_rows_are_marked_accrued_so_nobody_reads_them_as_an_invoice(self):
		client = Bag(servers=Bag(items=[hetzner_server(0, BYTES_PER_TB)]))

		row = hetzner_source().price_servers(client, hetzner_pricing(), DATE)[0]

		self.assertEqual(row["source"], "Accrued")
		self.assertEqual(row["provider"], "Hetzner")


def digitalocean_source():
	return DigitalOceanCostSource({"label": "do", "provider": "DigitalOcean", "cluster": "blr1"})


class TestDigitalOceanCostSource(FrappeTestCase):
	def test_droplets_are_priced_from_the_sizes_api(self):
		client = Bag(
			sizes=Bag(page={"sizes": [{"slug": "s-4vcpu-8gb", "price_monthly": 48.0}]}),
			droplets=Bag(
				page={
					"droplets": [
						{"size_slug": "s-4vcpu-8gb", "region": {"slug": "blr1"}},
						{"size_slug": "s-4vcpu-8gb", "region": {"slug": "blr1"}},
					]
				}
			),
		)

		rows = digitalocean_source().price_droplets(client, DATE, Bag(region="blr1"))

		self.assertEqual(rows[0]["usage_type"], "Droplet:s-4vcpu-8gb")
		self.assertEqual(rows[0]["usage_quantity"], 2)
		self.assertAlmostEqual(rows[0]["amortized_cost"], 2 * 48 / 30)

	def test_a_size_the_api_does_not_price_costs_nothing_rather_than_guessing(self):
		client = Bag(
			sizes=Bag(page={"sizes": []}),
			droplets=Bag(page={"droplets": [{"size_slug": "s-4vcpu-8gb", "region": {"slug": "blr1"}}]}),
		)

		rows = digitalocean_source().price_droplets(client, DATE, Bag(region="blr1"))

		self.assertEqual(rows[0]["amortized_cost"], 0)
		self.assertEqual(rows[0]["usage_quantity"], 1)

	def test_volumes_use_the_configured_rate(self):
		"""DigitalOcean publishes no price API for block storage, so the rate is a
		setting rather than a constant buried in the adapter."""
		client = Bag(volumes=Bag(page={"volumes": [{"size_gigabytes": 250, "region": {"slug": "blr1"}}]}))

		rows = digitalocean_source().price_volumes(client, DATE, Bag(region="blr1"), 0.10)

		self.assertAlmostEqual(rows[0]["amortized_cost"], 250 * 0.10 / 30)

	def test_snapshots_use_the_configured_rate(self):
		client = Bag(snapshots=Bag(page={"snapshots": [{"size_gigabytes": 40}]}))

		rows = digitalocean_source().price_snapshots(client, DATE, Bag(region="blr1"), 0.06)

		self.assertAlmostEqual(rows[0]["amortized_cost"], 40 * 0.06 / 30)


def usage_item(service, sku, amount, quantity, currency="USD"):
	return Bag(
		time_usage_started=datetime(2026, 8, 1, 0, 0),
		service=service,
		sku_name=sku,
		sku_part_number="B00000",
		region="ap-mumbai-1",
		computed_amount=amount,
		computed_quantity=quantity,
		unit="GB_MS",
		currency=currency,
	)


class TestOCICostSource(FrappeTestCase):
	def setUp(self):
		self.source = OCICostSource({"label": "oci", "provider": "OCI", "cluster": "mumbai"})

	def test_usage_rows_are_keyed_by_the_day_they_started(self):
		rows_by_date = {}
		self.source.collect([usage_item("COMPUTE", "Standard E4 - OCPU Hour", 12.5, 700)], rows_by_date)

		self.assertEqual(list(rows_by_date), ["2026-08-01"])
		row = rows_by_date["2026-08-01"][0]
		self.assertEqual(row["service"], "COMPUTE")
		self.assertEqual(row["usage_type"], "Standard E4 - OCPU Hour")
		self.assertEqual(row["region"], "ap-mumbai-1")
		self.assertAlmostEqual(row["amortized_cost"], 12.5)
		self.assertAlmostEqual(row["usage_quantity"], 700)

	def test_the_tenancy_currency_is_taken_from_the_response(self):
		rows_by_date = {}
		self.source.collect([usage_item("COMPUTE", "OCPU Hour", 1, 1, currency="INR")], rows_by_date)

		self.assertEqual(rows_by_date["2026-08-01"][0]["currency"], "INR")

	def test_a_sku_without_a_name_falls_back_to_its_part_number(self):
		item = usage_item("COMPUTE", None, 1, 1)
		rows_by_date = {}
		self.source.collect([item], rows_by_date)

		self.assertEqual(rows_by_date["2026-08-01"][0]["usage_type"], "B00000")

	def test_rows_are_marked_billed_because_oci_meters_like_aws(self):
		rows_by_date = {}
		self.source.collect([usage_item("COMPUTE", "OCPU Hour", 1, 1)], rows_by_date)

		self.assertEqual(rows_by_date["2026-08-01"][0]["source"], "Billed")
		self.assertEqual(rows_by_date["2026-08-01"][0]["provider"], "OCI")
