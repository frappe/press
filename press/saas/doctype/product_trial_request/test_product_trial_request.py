# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.saas.doctype.ai_settings.ai_settings import AISettings
from press.saas.doctype.ai_settings.test_ai_settings import enrolled
from press.saas.doctype.product_trial_request.product_trial_request import (
	revoke_archived_trial_keys,
)

KEY_ROW = {
	"name": "k1",
	"title": "s.test",
	"geography": "ap-south",
	"gateway_url": "https://gw",
	"api_key": "gr_x",  # pragma: allowlist secret
}


def queued(enqueue_doc) -> list[str]:
	"""The doc methods enqueued so far; Press queues other jobs of its own around a site."""
	return [call.args[2] for call in enqueue_doc.call_args_list if len(call.args) > 2]


def request_for(site, **fields):
	return frappe.get_doc({"doctype": "Product Trial Request", "site": site, **fields}).insert()


@patch.object(Site, "create_sync_user_webhook", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestProductTrialRequest(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("frappe.enqueue_doc")
	def test_a_site_created_queues_the_grove_key_only_while_press_is_enrolled(self, enqueue_doc):
		enrolled(control_api_key="", control_api_secret="")
		site = create_test_site()
		request = request_for(site.name, status="Wait for Site")
		request.status = "Site Created"
		request.save()
		self.assertFalse(request.grove_key_status)
		self.assertNotIn("provision_grove_key", queued(enqueue_doc))

		enrolled()
		request = request_for(site.name, status="Wait for Site")
		request.status = "Site Created"
		request.save()
		self.assertEqual(request.grove_key_status, "Pending")
		enqueue_doc.assert_any_call(
			"Product Trial Request", request.name, "provision_grove_key", enqueue_after_commit=True
		)

	def test_the_job_puts_the_key_in_the_site_config_as_ai_keys(self):
		enrolled()
		site = create_test_site()
		request = request_for(site.name, status="Pending")
		with patch.object(AISettings, "trial_key", return_value=KEY_ROW) as trial_key:
			request.provision_grove_key()
		trial_key.assert_called_once_with(site.name)
		self.assertEqual(frappe.get_doc("Site", site.name).get_config_value_for_key("ai_keys"), [KEY_ROW])
		self.assertEqual(
			frappe.db.get_value("Site Config Key", "ai_keys", ["internal", "type"], as_dict=True),
			{"internal": 1, "type": "JSON"},
		)
		self.assertEqual(frappe.db.get_value(request.doctype, request.name, "grove_key_status"), "Created")

	def test_a_refused_mint_is_failed_and_logged(self):
		enrolled()
		request = request_for(create_test_site().name, status="Pending")
		# log_error re-raises under test; outside a test it writes the Error Log and the job ends.
		with (
			patch.object(AISettings, "trial_key", side_effect=frappe.ValidationError("Grove refused")),
			self.assertRaisesRegex(frappe.ValidationError, "Grove refused"),
		):
			request.provision_grove_key()
		self.assertEqual(frappe.db.get_value(request.doctype, request.name, "grove_key_status"), "Failed")

	def test_the_hourly_job_revokes_the_keys_of_archived_trial_sites(self):
		enrolled()
		gone = create_test_site()
		alive = create_test_site(bench=gone.bench)
		frappe.db.set_value("Site", gone.name, "status", "Archived")
		requests = {name: request_for(name, grove_key_status="Created") for name in (gone.name, alive.name)}

		with patch.object(AISettings, "revoke_trial_key") as revoke:
			revoke_archived_trial_keys()
		revoke.assert_called_once_with(gone.name)
		self.assertEqual(
			{
				name: frappe.db.get_value("Product Trial Request", r.name, "grove_key_status")
				for name, r in requests.items()
			},
			{gone.name: "Revoked", alive.name: "Created"},
		)

		frappe.db.set_value("Product Trial Request", requests[gone.name].name, "grove_key_status", "Created")
		with (
			patch.object(AISettings, "revoke_trial_key", side_effect=frappe.ValidationError("6 hours")),
			self.assertRaisesRegex(frappe.ValidationError, "6 hours"),
		):
			revoke_archived_trial_keys()
		self.assertEqual(
			frappe.db.get_value("Product Trial Request", requests[gone.name].name, "grove_key_status"),
			"Created",
		)
