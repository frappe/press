# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.ai_settings.ai_settings import AISettings
from press.saas.doctype.ai_settings.test_ai_settings import enrolled
from press.saas.doctype.grove_key_request.grove_key_request import (
	MAX_ATTEMPTS,
	revoke_archived,
	run_pending,
)

MINTED = {
	"name": "k1",
	"geography": "ap-south",
	"gateway_url": "https://gw",
	"api_key": "gr_x",  # pragma: allowlist secret
}  # pragma: allowlist secret


def request_for(site):
	"""A request as Site Created makes one, its immediate job held back."""
	with patch("frappe.enqueue_doc") as enqueue_doc:
		doc = frappe.get_doc({"doctype": "Grove Key Request", "site": site}).insert()
	enqueue_doc.assert_called_once_with("Grove Key Request", doc.name, "attempt", enqueue_after_commit=True)
	return doc


def ai_keys_of(site) -> list | None:
	return frappe.get_doc("Site", site).get_config_value_for_key("ai_keys")


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestGroveKeyRequest(FrappeTestCase):
	def setUp(self):
		enrolled()

	def tearDown(self):
		frappe.db.rollback()

	def test_a_try_mints_once_and_puts_the_key_in_the_site_config(self):
		doc = request_for(create_test_site().name)
		with patch.object(AISettings, "provision_key", return_value=MINTED) as provision_key:
			doc.attempt()
		provision_key.assert_called_once_with(doc.site)
		self.assertEqual(ai_keys_of(doc.site), [{**MINTED, "title": doc.site}])
		self.assertEqual(
			frappe.db.get_value("Site Config Key", "ai_keys", ["internal", "type"], as_dict=True),
			{"internal": 1, "type": "JSON"},
		)
		doc.reload()
		self.assertEqual(
			(doc.status, doc.grove_key, doc.attempts, doc.get_password("api_key", raise_exception=False)),
			("Success", "k1", 0, None),
		)
		with patch.object(AISettings, "provision_key") as provision_key:
			doc.attempt()
		provision_key.assert_not_called()

	def test_a_failed_try_counts_keeps_pending_and_gives_up_at_the_cap(self):
		doc = request_for(create_test_site().name)
		refused = frappe.ValidationError("Grove can't be reached right now.")
		with patch.object(AISettings, "provision_key", side_effect=refused):
			doc.attempt()
			doc.reload()
			self.assertEqual(
				(doc.status, doc.attempts, doc.last_error),
				("Pending", 1, "Grove can't be reached right now."),
			)
			doc.db_set("attempts", MAX_ATTEMPTS - 1)
			doc.attempt()
		doc.reload()
		self.assertEqual((doc.status, doc.attempts, doc.grove_key), ("Failed", MAX_ATTEMPTS, None))
		self.assertIsNone(ai_keys_of(doc.site))

	def test_a_half_done_try_keeps_the_minted_key_and_leaves_no_config_behind(self):
		doc = request_for(create_test_site().name)
		with (
			patch.object(AISettings, "provision_key", return_value=MINTED),
			patch.object(Site, "update_site_config", side_effect=Exception("agent down")),
		):
			doc.attempt()
		doc.reload()
		self.assertEqual(
			(doc.status, doc.attempts, doc.grove_key, doc.get_password("api_key")),
			("Pending", 1, "k1", "gr_x"),
		)
		self.assertFalse(frappe.db.exists("Site Config Key", {"key": "ai_keys"}))
		with patch.object(AISettings, "provision_key") as provision_key:
			doc.attempt()
		provision_key.assert_not_called()
		doc.reload()
		self.assertEqual((doc.status, doc.get_password("api_key", raise_exception=False)), ("Success", None))
		self.assertEqual(ai_keys_of(doc.site)[0]["api_key"], "gr_x")

	def test_the_cron_takes_only_rows_the_immediate_job_has_not_touched_lately(self):
		site = create_test_site()
		fresh, stale = request_for(site.name), request_for(create_test_site(bench=site.bench).name)
		frappe.db.set_value(
			"Grove Key Request",
			stale.name,
			"modified",
			add_to_date(now_datetime(), minutes=-10),
			update_modified=False,
		)
		with patch.object(AISettings, "provision_key", return_value=MINTED):
			run_pending()
		self.assertEqual(
			[frappe.db.get_value("Grove Key Request", d.name, "status") for d in (fresh, stale)],
			["Pending", "Success"],
		)

	def test_retry_starts_a_failed_row_over(self):
		doc = request_for(create_test_site().name)
		doc.db_set({"status": "Failed", "attempts": MAX_ATTEMPTS, "last_error": "x"})
		with patch.object(AISettings, "provision_key", return_value=MINTED):
			doc.retry()
		doc.reload()
		self.assertEqual((doc.status, doc.attempts, doc.last_error, doc.grove_key), ("Success", 0, "", "k1"))

	def test_an_archived_sites_key_is_revoked_hourly_and_a_refusal_waits(self):
		site = create_test_site()
		gone, alive = request_for(site.name), request_for(create_test_site(bench=site.bench).name)
		for doc in (gone, alive):
			doc.db_set({"status": "Success", "grove_key": f"key-{doc.name}"})
		frappe.db.set_value("Site", gone.site, "status", "Archived")

		with patch.object(AISettings, "revoke_key", side_effect=frappe.ValidationError("6 hours")):
			revoke_archived()
		gone.reload()
		self.assertEqual((gone.status, gone.last_error), ("Success", "6 hours"))

		with patch.object(AISettings, "revoke_key") as revoke_key:
			revoke_archived()
		revoke_key.assert_called_once_with(f"key-{gone.name}")
		self.assertEqual(
			[frappe.db.get_value("Grove Key Request", d.name, "status") for d in (gone, alive)],
			["Revoked", "Success"],
		)
