# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.grove_settings.grove_settings import GroveSettings
from press.saas.doctype.grove_settings.test_grove_settings import enrolled
from press.saas.doctype.grove_trial_key import grove_trial_key
from press.saas.doctype.grove_trial_key.grove_trial_key import GroveTrialKey

MODULE = "press.saas.doctype.grove_trial_key.grove_trial_key"
GATEWAY = "https://gw"


def minted(name: str) -> dict:
	return {"name": name, "geography": "ap-south", "gateway_url": GATEWAY, "api_key": f"gr_{name}"}


def available() -> GroveTrialKey:
	"""A pool key as the refill job holds one, without a Grove."""
	reply = minted(frappe.generate_hash(length=10))
	return frappe.get_doc(
		{
			"doctype": "Grove Trial Key",
			"grove_key": reply["name"],
			"team": "Press Team",
			"geography": reply["geography"],
			"gateway_url": reply["gateway_url"],
			"api_key": reply["api_key"],
		}
	).insert()


def request_for(site: str, name: str = "PTR-1") -> Mock:
	"""What `assign` reads off a Product Trial Request."""
	request = Mock(site=site)
	request.name = name
	return request


def ai_keys_of(site: str) -> list | None:
	return frappe.get_doc("Site", site).get_config_value_for_key("ai_keys")


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestGroveTrialKey(FrappeTestCase):
	def setUp(self):
		# A revoke commits so the record outlives a failed job; tests roll back instead.
		self.start(patch.object(frappe.db, "commit"))
		self.provision = self.start(
			patch.object(
				GroveSettings, "provision_key", side_effect=lambda: minted(frappe.generate_hash(length=10))
			)
		)
		self.revoke = self.start(patch.object(GroveSettings, "revoke_key"))
		# A live run leaves real pool rows on the site; the counts here assume none.
		frappe.db.delete("Grove Trial Key")
		enrolled(trial_pool_size=3)

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

	def test_refill_mints_only_the_missing_keys_under_the_trial_team(self):
		available()

		grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), ["Available"] * 3)
		self.assertEqual(self.provision.call_count, 2)
		key = frappe.get_doc("Grove Trial Key", frappe.get_all("Grove Trial Key", pluck="name")[-1])
		self.assertEqual(
			(key.team, key.geography, key.gateway_url, key.get_password("api_key")),
			("Press Team", "ap-south", GATEWAY, f"gr_{key.grove_key}"),
		)

	def test_refill_mints_at_most_one_batch(self):
		enrolled(trial_pool_size=5)

		with patch(f"{MODULE}.REFILL_BATCH_SIZE", 2):
			grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), ["Available"] * 2)

	def test_a_failed_mint_stops_the_batch(self):
		self.provision.side_effect = Exception("Grove is down")

		with patch(f"{MODULE}.frappe.log_error") as log_error:
			grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), [])
		log_error.assert_called_once()

	def test_refill_does_nothing_while_the_pool_is_off_or_press_is_not_enrolled(self):
		enrolled(trial_pool_size=0)
		grove_trial_key.refill_trial_keys()
		enrolled(trial_pool_size=3, control_api_key="", control_api_secret="")
		grove_trial_key.refill_trial_keys()

		self.assertEqual(self.statuses(), [])
		self.provision.assert_not_called()

	def test_a_site_takes_the_oldest_key_and_a_repeated_site_created_keeps_it(self):
		first, second = available(), available()

		taken = GroveTrialKey.assign(request_for("a.test"))
		again = GroveTrialKey.assign(request_for("a.test", "PTR-2"))
		other = GroveTrialKey.assign(request_for("b.test", "PTR-3"))

		self.assertEqual((taken.name, again.name, other.name), (first.name, first.name, second.name))
		first.reload()
		self.assertEqual(
			(first.status, first.site, first.product_trial_request), ("Assigned", "a.test", "PTR-1")
		)
		self.assertIsNone(GroveTrialKey.assign(request_for("c.test", "PTR-4")))

	def test_the_key_goes_into_the_site_config_as_an_internal_key(self):
		site = create_test_site()
		key = available()
		GroveTrialKey.assign(request_for(site.name))

		key.reload()
		key.write_config()

		self.assertEqual(ai_keys_of(site.name), [{"gateway_url": GATEWAY, "api_key": f"gr_{key.grove_key}"}])
		self.assertEqual(
			frappe.db.get_value("Site Config Key", "ai_keys", ["internal", "type"], as_dict=True),
			{"internal": 1, "type": "JSON"},
		)

	def test_an_archived_sites_key_is_queued_for_revoke_hourly_and_the_job_revokes_it(self):
		site = create_test_site()
		gone, alive = available(), available()
		GroveTrialKey.assign(request_for(site.name))
		GroveTrialKey.assign(request_for(create_test_site(bench=site.bench).name, "PTR-2"))
		frappe.db.set_value("Site", site.name, "status", "Archived")

		with patch(f"{MODULE}.frappe.enqueue") as enqueue:
			grove_trial_key.revoke_archived()

		self.assertEqual([d.reload().status for d in (gone, alive)], ["Revoking", "Assigned"])
		self.assertEqual(enqueue.call_args.kwargs["name"], gone.name)
		grove_trial_key.revoke_trial_key(gone.name)
		self.revoke.assert_called_once_with(gone.grove_key, "Press Team")
		self.assertEqual(gone.reload().status, "Revoked")

	def test_a_refused_revoke_stays_revoking_and_is_tried_again_once_stale(self):
		key = available()
		self.revoke.side_effect = frappe.ValidationError("6 hours")
		with patch(f"{MODULE}.frappe.enqueue"):
			key.revoke()

		grove_trial_key.retry_revokes()
		self.revoke.assert_not_called()

		self.age(key)
		with patch(f"{MODULE}.frappe.log_error") as log_error:
			grove_trial_key.retry_revokes()
		self.assertEqual((key.reload().status, log_error.call_count), ("Revoking", 1))
		# The failed attempt wrote the record, so the next run waits another hour.
		self.revoke.reset_mock()
		grove_trial_key.retry_revokes()
		self.revoke.assert_not_called()

		self.revoke.side_effect = None
		self.age(key)
		grove_trial_key.retry_revokes()
		self.assertEqual(key.reload().status, "Revoked")

	def test_only_a_revoked_record_can_be_deleted(self):
		key = available()

		with self.assertRaisesRegex(frappe.ValidationError, "Revoke Key"):
			key.delete()
		key.db_set("status", "Revoked")
		key.delete()
		self.assertFalse(frappe.db.exists("Grove Trial Key", key.name))
