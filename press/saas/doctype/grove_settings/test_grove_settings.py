# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from contextlib import contextmanager
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.saas.doctype.grove_settings import grove_settings
from press.saas.doctype.product_trial.test_product_trial import create_test_product_trial


def product_trial(key: str = "grove-trial-a") -> str:
	"""A Product Trial for a pool row, made once per site."""
	if not frappe.db.exists("Product Trial", key):
		create_test_product_trial(create_test_app(key, key.title()))
	return key


def pool_rows(sizes: dict[str, int], groups: dict[str, str] | None = None) -> list[dict]:
	"""Trial Products rows: one per product in `sizes` ({key: size}), in the Model Group `groups`
	names for it, if any."""
	return [
		{"product_trial": product_trial(key), "pool_size": size, "model_group": (groups or {}).get(key)}
		for key, size in sizes.items()
	]


def enrolled(**fields):
	"""Grove Settings as an enrolled Press would hold them, without a Grove: one pool of two."""
	settings = frappe.get_single("Grove Settings")
	settings.update(
		{
			"base_url": "http://grove.test/",
			"control_api_key": "K",
			"control_api_secret": "S",  # pragma: allowlist secret
			"trial_team": "Press Team",
			"trial_key_geography": "ap-south",
			"trial_key_cap": 2,
			"trial_key_revoke_after_days": 30,
			"pause_pool_refill": 0,
			"pause_key_assignment": 0,
			"trial_products": pool_rows({"grove-trial-a": 2}),
		}
		| fields
	)
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

	def test_enroll_mints_the_credential_and_calls_grove_for_nothing_else(self):
		enrolled(control_api_key="", control_api_secret="")
		with grove_replies({"api_key": "K2", "api_secret": "S2"}) as post:  # pragma: allowlist secret
			frappe.local.form_dict.bootstrap_secret = "boot"  # pragma: allowlist secret
			grove_settings.enroll()
		self.assertEqual(post.call_count, 1)
		self.assertEqual(
			sent(post),
			(
				"grove.api.control.create_control_client",
				{"email": f"press@{frappe.local.site}", "token": "boot"},
				None,
			),
		)
		settings = frappe.get_single("Grove Settings")
		self.assertEqual(
			(settings.control_api_key, settings.get_password("control_api_secret"), settings.is_enrolled),
			("K2", "S2", True),
		)

	def test_a_pool_key_is_minted_titled_by_the_record_in_the_trial_geography_at_the_cap_in_the_rows_group(
		self,
	):
		settings = enrolled(
			trial_key_cap=3,
			trial_products=pool_rows(
				{"grove-trial-a": 2, "grove-trial-b": 1}, groups={"grove-trial-b": "crm-trial"}
			),
		)
		row = {
			"name": "k1",
			"geography": "ap-south",
			"gateway_url": "https://gw",
			"api_key": "gr_x",  # pragma: allowlist secret
		}  # pragma: allowlist secret
		with grove_replies(row) as post:
			self.assertEqual(settings.provision_key(settings.trial_products[0], "GTK-00001"), row)
			settings.provision_key(settings.trial_products[1], "GTK-00002")
		self.assertEqual(
			sent(post, 0),
			(
				"grove.api.keys.provision_key",
				{"team": "Press Team", "title": "GTK-00001", "geography": "ap-south", "cap": 3},
				{"Authorization": "token K:S"},
			),
		)
		self.assertEqual(sent(post, 1)[1]["model_groups"], ["crm-trial"])
		with grove_replies("Revoked.") as post:
			settings.revoke_key("k1", "Press Trials")
		self.assertEqual(sent(post)[:2], ("grove.api.keys.revoke_key", {"team": "Press Trials", "key": "k1"}))
		with grove_replies([]) as post:
			settings.update_caps("Press Team", {"k1": 5})
		self.assertEqual(
			sent(post)[:2], ("grove.api.keys.update_caps", {"team": "Press Team", "caps": {"k1": 5}})
		)

	def test_groves_own_refusal_is_what_the_caller_reads(self):
		settings = enrolled()
		row = settings.trial_products[0]
		refusal = json.dumps([json.dumps({"message": "This team already holds 2 live keys, its limit."})])
		with grove_replies(None, status=417) as post:
			post.return_value.json.return_value = {"_server_messages": refusal}
			with self.assertRaisesRegex(frappe.ValidationError, "already holds 2 live keys"):
				settings.provision_key(row, "GTK-00001")
		with grove_replies(None, status=503), self.assertRaisesRegex(frappe.ValidationError, "unavailable"):
			settings.provision_key(row, "GTK-00001")

	def test_a_sized_pool_needs_a_geography_and_one_row_per_product(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Trial Key Geography"):
			enrolled(trial_key_geography="")
		enrolled(trial_key_geography="", trial_products=pool_rows({"grove-trial-a": 0}))
		enrolled(trial_key_geography="", trial_products=[])
		with self.assertRaisesRegex(frappe.ValidationError, "One pool row per product"):
			enrolled(trial_products=pool_rows({"grove-trial-a": 1}) * 2)

	def test_not_enrolled_is_refused_before_any_call(self):
		settings = enrolled(control_api_key="", control_api_secret="")
		with grove_replies({}) as post, self.assertRaisesRegex(frappe.ValidationError, "enroll Press"):
			settings.provision_key(settings.trial_products[0], "GTK-00001")
		post.assert_not_called()
