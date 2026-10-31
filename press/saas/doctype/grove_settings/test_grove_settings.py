# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.saas.doctype.grove_settings import grove_settings
from press.saas.doctype.grove_settings.grove_settings import PRESS_TIER


def enrolled(**fields):
	"""Grove Settings as an enrolled Press would hold them, without a Grove."""
	settings = frappe.get_single("Grove Settings")
	settings.update(
		{
			"base_url": "http://grove.test/",
			"control_api_key": "K",
			"control_api_secret": "S",  # pragma: allowlist secret
			"trial_team": "Press Team",
			"trial_key_geography": "ap-south",
			"trial_pool_size": 2,
			"trial_key_expiry": "Never",
			"trial_key_cap": 2,
		}
		| fields
	)
	with grove_replies({}):  # a changed trial team registers itself at Grove
		settings.save()
	return frappe.get_cached_doc("Grove Settings")


@contextmanager
def grove_replies(message, status=200):
	with patch("press.saas.doctype.grove_settings.grove_settings.requests.post") as post:
		post.return_value.status_code = status
		post.return_value.json.return_value = {"message": message}
		yield post


def sent(post, index=-1) -> tuple[str, dict, dict | None]:
	"""(Grove method, JSON body, headers) of one call Press made."""
	call = post.call_args_list[index]
	return call.args[0].rsplit("/api/method/", 1)[1], call.kwargs["json"], call.kwargs.get("headers")


class TestGroveSettings(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_enroll_mints_the_credential_then_registers_the_team_on_its_tier(self):
		enrolled(control_api_key="", control_api_secret="")
		with grove_replies({"api_key": "K2", "api_secret": "S2"}) as post:  # pragma: allowlist secret
			frappe.local.form_dict.bootstrap_secret = "boot"  # pragma: allowlist secret
			grove_settings.enroll()
		calls = [sent(post, i) for i in range(3)]
		self.assertEqual(
			calls[0],
			(
				"grove.api.control.create_control_client",
				{"email": f"press@{frappe.local.site}", "token": "boot"},
				None,
			),
		)
		self.assertEqual(calls[1][:2], ("grove.api.teams.provision_team", {"team": "Press Team"}))
		self.assertEqual(
			calls[2],
			(
				"grove.api.teams.update_team",
				{"team": "Press Team", "tier": PRESS_TIER},
				{"Authorization": "token K2:S2"},
			),
		)
		settings = frappe.get_single("Grove Settings")
		self.assertEqual(
			(settings.control_api_key, settings.get_password("control_api_secret"), settings.is_enrolled),
			("K2", "S2", True),
		)

	def test_a_pool_key_is_minted_untitled_in_the_trial_geography_at_the_cap_and_expiry(self):
		settings = enrolled(trial_key_cap=3, trial_key_expiry="7 Days")
		row = {
			"name": "k1",
			"geography": "ap-south",
			"gateway_url": "https://gw",
			"api_key": "gr_x",  # pragma: allowlist secret
		}  # pragma: allowlist secret
		with grove_replies(row) as post:
			self.assertEqual(settings.provision_key(), row)
		self.assertEqual(
			sent(post),
			(
				"grove.api.keys.provision_key",
				{
					"team": "Press Team",
					"title": None,
					"geography": "ap-south",
					"cap": 3,
					"expiry": "7 Days",
					"expiry_from_first_use": True,
				},
				{"Authorization": "token K:S"},
			),
		)
		with grove_replies("Revoked.") as post:
			settings.revoke_key("k1", "Press Trials")
		self.assertEqual(sent(post)[:2], ("grove.api.keys.revoke_key", {"team": "Press Trials", "key": "k1"}))

	def test_a_changed_trial_team_is_registered_at_grove_and_a_quiet_save_is_not(self):
		settings = enrolled()
		with grove_replies({}) as post:
			settings.trial_team = "Press Trials"
			settings.save()
		self.assertEqual(
			[sent(post, i)[:2] for i in range(2)],
			[
				("grove.api.teams.provision_team", {"team": "Press Trials"}),
				("grove.api.teams.update_team", {"team": "Press Trials", "tier": PRESS_TIER}),
			],
		)
		with grove_replies({}) as post:
			settings.trial_key_cap = 5
			settings.save()
		post.assert_not_called()
		settings = enrolled(control_api_key="", control_api_secret="")
		with grove_replies({}) as post:
			settings.trial_team = "Press Trials 2"
			settings.save()
		post.assert_not_called()

	def test_groves_own_refusal_is_what_the_caller_reads(self):
		settings = enrolled()
		refusal = json.dumps([json.dumps({"message": "This team already holds 2 live keys, its limit."})])
		with grove_replies(None, status=417) as post:
			post.return_value.json.return_value = {"_server_messages": refusal}
			with self.assertRaisesRegex(frappe.ValidationError, "already holds 2 live keys"):
				settings.provision_key()
		with grove_replies(None, status=503), self.assertRaisesRegex(frappe.ValidationError, "unavailable"):
			settings.provision_key()

	def test_a_sized_pool_needs_a_geography(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Trial Key Geography"):
			enrolled(trial_key_geography="")
		enrolled(trial_key_geography="", trial_pool_size=0)

	def test_not_enrolled_is_refused_before_any_call(self):
		settings = enrolled(control_api_key="", control_api_secret="")
		with grove_replies({}) as post, self.assertRaisesRegex(frappe.ValidationError, "enroll Press"):
			settings.provision_key()
		post.assert_not_called()
