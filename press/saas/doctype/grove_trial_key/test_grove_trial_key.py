# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.grove_settings.grove_settings import GroveSettings
from press.saas.doctype.grove_settings.test_grove_settings import enrolled, pool_rows, product_trial
from press.saas.doctype.grove_trial_key import grove_trial_key
from press.saas.doctype.grove_trial_key.grove_trial_key import GroveTrialKey

MODULE = "press.saas.doctype.grove_trial_key.grove_trial_key"
GATEWAY = "https://gw"
PRODUCT, OTHER = "grove-trial-a", "grove-trial-b"


def minted(name: str) -> dict:
	return {"name": name, "geography": "ap-south", "gateway_url": GATEWAY, "api_key": f"gr_{name}"}


def available(product: str = PRODUCT) -> GroveTrialKey:
	"""A pool key as the refill job holds one, without a Grove."""
	reply = minted(frappe.generate_hash(length=10))
	return frappe.get_doc(
		{
			"doctype": "Grove Trial Key",
			"grove_key": reply["name"],
			"product_trial": product_trial(product),
			"team": "Press Team",
			"geography": reply["geography"],
			"gateway_url": reply["gateway_url"],
			"cap": 2,
			"api_key": reply["api_key"],
		}
	).insert()


def site_named(name: str) -> Site:
	"""A site before its insert, as `assign` takes one: a name and an empty configuration."""
	return frappe.get_doc(doctype="Site", name=name)


def pools(sizes: dict[str, int], groups: dict[str, str] | None = None, **fields):
	return enrolled(trial_products=pool_rows(sizes, groups), **fields)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestGroveTrialKey(FrappeTestCase):
	def setUp(self):
		# A revoke commits so the record outlives a failed job; tests roll back instead.
		self.start(patch.object(frappe.db, "commit"))
		self.provision = self.start(
			patch.object(
				GroveSettings,
				"provision_key",
				side_effect=lambda row, title: minted(frappe.generate_hash(length=10)),
			)
		)
		self.revoke = self.start(patch.object(GroveSettings, "revoke_key"))
		self.update_caps = self.start(patch.object(GroveSettings, "update_caps"))
		# A live run leaves real pool rows on the site; the counts here assume none.
		frappe.db.delete("Grove Trial Key")
		pools({PRODUCT: 3})

	def tearDown(self):
		frappe.db.rollback()

	def start(self, patcher):
		self.addCleanup(patcher.stop)
		return patcher.start()

	def statuses(self) -> list[str]:
		return frappe.get_all("Grove Trial Key", pluck="status", order_by="creation asc")

	def age(self, key: GroveTrialKey) -> None:
		frappe.db.set_value(
			"Grove Trial Key",
			key.name,
			"modified",
			add_to_date(now_datetime(), minutes=-61),
			update_modified=False,
		)

	def age_assignment(self, key: GroveTrialKey, days: int = 31) -> None:
		frappe.db.set_value(
			"Grove Trial Key",
			key.name,
			"assigned_at",
			add_to_date(now_datetime(), days=-days),
			update_modified=False,
		)

	def test_refill_mints_only_the_missing_keys_under_the_trial_team(self):
		available()

		grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), ["Available"] * 3)
		self.assertEqual(self.provision.call_count, 2)
		key = frappe.get_doc(
			"Grove Trial Key", frappe.get_all("Grove Trial Key", pluck="name", order_by="creation asc")[-1]
		)
		self.assertEqual(
			(
				key.team,
				key.product_trial,
				key.geography,
				key.gateway_url,
				key.cap,
				key.get_password("api_key"),
			),
			("Press Team", PRODUCT, "ap-south", GATEWAY, 2, f"gr_{key.grove_key}"),
		)
		# The record has an id of its own, and that id is the key's title at Grove.
		self.assertTrue(key.name.startswith("GTK-") and key.name != key.grove_key)
		self.assertEqual(self.provision.call_args.kwargs["title"], key.name)

	def test_each_product_is_refilled_to_its_size_in_its_group_within_one_batch(self):
		pools({PRODUCT: 2, OTHER: 2}, groups={OTHER: "crm-trial"})
		available()

		with patch(f"{MODULE}.REFILL_BATCH_SIZE", 2):
			grove_trial_key.refill_trial_keys()

		self.assertEqual(
			frappe.get_all("Grove Trial Key", pluck="product_trial", order_by="creation asc"),
			[PRODUCT, PRODUCT, OTHER],
		)
		self.assertEqual(
			[call.args[0].model_group for call in self.provision.call_args_list], [None, "crm-trial"]
		)

	def test_refill_mints_at_most_one_batch(self):
		pools({PRODUCT: 5})

		with patch(f"{MODULE}.REFILL_BATCH_SIZE", 2):
			grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), ["Available"] * 2)

	def test_a_failed_mint_stops_the_batch(self):
		self.provision.side_effect = Exception("Grove is down")

		with patch(f"{MODULE}.frappe.log_error") as log_error:
			grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), [])
		log_error.assert_called_once()

	def test_refill_does_nothing_while_the_pools_are_off_or_press_is_not_enrolled(self):
		pools({PRODUCT: 0})
		grove_trial_key.refill_trial_keys()
		pools({PRODUCT: 3}, control_api_key="", control_api_secret="")
		grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), [])
		self.provision.assert_not_called()

	def test_a_pending_revoke_is_retried_with_the_pool_off_or_paused(self):
		key = available()
		with patch(f"{MODULE}.frappe.enqueue"):
			GroveTrialKey.queue_revoke(name=key.name)
		self.age(key)
		pools({PRODUCT: 0})

		grove_trial_key.refill_trial_keys()

		self.assertEqual(key.reload().status, "Revoked")
		self.provision.assert_not_called()

		pools({PRODUCT: 3}, pause_pool_refill=1)
		with patch(f"{MODULE}.retry_revokes") as retry_revokes:
			grove_trial_key.refill_trial_keys()
		retry_revokes.assert_called_once()
		self.provision.assert_not_called()

	def test_a_site_takes_the_oldest_key_of_its_product_into_its_configuration(self):
		first, second, others = available(), available(), available(OTHER)
		site = site_named("a.test")

		taken = GroveTrialKey.assign(site, PRODUCT, "PTR-1")
		other = GroveTrialKey.assign(site_named("b.test"), PRODUCT)

		self.assertEqual((taken.name, other.name), (first.name, second.name))
		first.reload()
		self.assertEqual(
			(first.status, first.site, first.product_trial_request), ("Assigned", "a.test", "PTR-1")
		)
		self.assertEqual(
			site.get_config_value_for_key("ai_keys"),
			[{"gateway_url": GATEWAY, "api_key": f"gr_{first.grove_key}"}],
		)
		self.assertIsNone(GroveTrialKey.assign(site_named("c.test"), PRODUCT))
		self.assertEqual(GroveTrialKey.assign(site_named("d.test"), OTHER).name, others.name)

	def test_paused_assignment_leaves_the_ready_key_in_the_pool(self):
		key = available()
		pools({PRODUCT: 3}, pause_key_assignment=1)

		self.assertIsNone(GroveTrialKey.assign(site_named("a.test"), PRODUCT))
		self.assertEqual(key.reload().status, "Available")

	def test_the_key_is_written_under_an_internal_site_config_key(self):
		available()

		GroveTrialKey.assign(site_named("a.test"), PRODUCT)

		self.assertEqual(
			frappe.db.get_value("Site Config Key", "ai_keys", ["internal", "type"], as_dict=True),
			{"internal": 1, "type": "JSON"},
		)

	def test_only_a_running_sites_cap_can_be_raised_and_only_upward(self):
		key = available()
		with self.assertRaisesRegex(frappe.ValidationError, "running trial site"):
			key.raise_cap(5)

		GroveTrialKey.assign(site_named("a.test"), PRODUCT)
		key.reload().raise_cap(5)
		self.update_caps.assert_called_once_with("Press Team", {key.grove_key: 5})
		self.assertEqual(key.reload().cap, 5)
		with self.assertRaisesRegex(frappe.ValidationError, "already"):
			key.raise_cap(5)

		for status in ("Revoking", "Revoked"):
			key.db_set("status", status)
			with self.assertRaisesRegex(frappe.ValidationError, "running trial site"):
				key.reload().raise_cap(9)
		self.update_caps.assert_called_once()

	def test_an_assigned_key_is_revoked_once_its_days_have_passed(self):
		pools({PRODUCT: 0})
		aged, fresh = available(), available()
		available()
		GroveTrialKey.assign(site_named("a.test"), PRODUCT)
		GroveTrialKey.assign(site_named("b.test"), PRODUCT)

		self.age_assignment(aged)
		with patch(f"{MODULE}.frappe.enqueue"):
			grove_trial_key.refill_trial_keys()
		self.assertEqual(self.statuses(), ["Revoking", "Assigned", "Available"])

		# 0 turns the stop off.
		pools({PRODUCT: 0}, trial_key_revoke_after_days=0)
		self.age_assignment(fresh)
		with patch(f"{MODULE}.frappe.enqueue"):
			grove_trial_key.refill_trial_keys()
		self.assertEqual(self.statuses(), ["Revoking", "Assigned", "Available"])

	def test_an_archived_sites_key_is_queued_for_revoke_hourly_and_the_job_revokes_it(self):
		site = create_test_site()
		gone, alive = available(), available()
		GroveTrialKey.assign(site, PRODUCT)
		GroveTrialKey.assign(create_test_site(bench=site.bench), PRODUCT)
		frappe.db.set_value("Site", site.name, "status", "Archived")

		with patch(f"{MODULE}.frappe.enqueue") as enqueue:
			grove_trial_key.revoke_archived()

		self.assertEqual([d.reload().status for d in (gone, alive)], ["Revoking", "Assigned"])
		self.assertEqual(enqueue.call_args.kwargs["name"], gone.name)
		grove_trial_key.revoke_trial_key(gone.name)
		self.revoke.assert_called_once_with(gone.grove_key, "Press Team")
		self.assertEqual(gone.reload().status, "Revoked")

	def test_a_refused_revoke_stays_revoking_with_groves_answer_and_is_tried_again_once_stale(self):
		key = available()
		self.revoke.side_effect = frappe.ValidationError("6 hours")
		with patch(f"{MODULE}.frappe.enqueue"):
			key.revoke()
		# The queued job itself: the refusal lands on the record, nothing raises.
		with patch(f"{MODULE}.frappe.log_error"):
			grove_trial_key.revoke_trial_key(key.name)
		self.assertEqual((key.reload().status, key.last_error), ("Revoking", "6 hours"))
		self.revoke.reset_mock()

		grove_trial_key.retry_revokes()
		self.revoke.assert_not_called()

		self.age(key)
		with patch(f"{MODULE}.frappe.log_error") as log_error:
			grove_trial_key.retry_revokes()
		self.assertEqual(
			(key.reload().status, key.last_error, log_error.call_count), ("Revoking", "6 hours", 1)
		)
		# The failed attempt wrote the record, so the next run waits another hour.
		self.revoke.reset_mock()
		grove_trial_key.retry_revokes()
		self.revoke.assert_not_called()

		self.revoke.side_effect = None
		self.age(key)
		grove_trial_key.retry_revokes()
		self.assertEqual((key.reload().status, key.last_error), ("Revoked", None))

	def test_only_a_revoked_record_can_be_deleted(self):
		key = available()

		with self.assertRaisesRegex(frappe.ValidationError, "Revoke Key"):
			key.delete()
		key.db_set("status", "Revoked")
		key.delete()
		self.assertFalse(frappe.db.exists("Grove Trial Key", key.name))
