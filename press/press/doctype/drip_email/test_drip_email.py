# Copyright (c) 2015, Web Notes and Contributors
# See license.txt

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan_change.test_site_plan_change import create_test_plan
from press.saas.doctype.product_trial.test_product_trial import create_test_product_trial

if TYPE_CHECKING:
	from press.press.doctype.drip_email.drip_email import DripEmail


def create_test_drip_email(
	send_after: int,
	product_trial: str | None = None,
	skip_sites_with_paid_plan: bool = False,
	email_type: str = "Drip",
) -> DripEmail:
	drip_email = frappe.get_doc(
		{
			"doctype": "Drip Email",
			"enabled": 1,
			"sender": "test@test.com",
			"sender_name": "Test User",
			"subject": "Drip Test",
			"message": "Drip Top, Drop Top",
			"email_type": email_type,
			"send_after": send_after,
			"product_trial": product_trial,
			"skip_sites_with_paid_plan": skip_sites_with_paid_plan,
		}
	).insert(ignore_if_duplicate=True)
	drip_email.reload()
	return drip_email


class TestDripEmail(FrappeTestCase):
	def setUp(self) -> None:
		self.trial_site_plan = create_test_plan("Site", is_trial_plan=True)
		self.paid_site_plan = create_test_plan("Site", is_trial_plan=False)

	def tearDown(self):
		frappe.db.rollback()

	def test_correct_sites_are_selected_for_drip_email(self):
		test_app = create_test_app("wiki", "Wiki")

		test_product_trial = create_test_product_trial(test_app)

		drip_email = create_test_drip_email(0, product_trial=test_product_trial.name)

		site1 = create_test_site(
			"site1",
			standby_for_product=test_product_trial.name,
			account_request=create_test_account_request(
				"site1", saas=True, product_trial=test_product_trial.name
			).name,
		)
		site1.save()

		site2 = create_test_site("site2", account_request=create_test_account_request("site2").name)
		site2.save()

		create_test_site("site3")  # Note: site is not created

		self.assertEqual(drip_email.sites_to_send_drip, [site1.name])

	def test_older_site_isnt_selected(self):
		drip_email = create_test_drip_email(0)
		site = create_test_site("site1")
		site.account_request = create_test_account_request("site1", creation=date.today() - timedelta(1)).name
		site.save()
		self.assertNotEqual(drip_email.sites_to_send_drip, [site.name])

	def test_drip_emails_not_sent_to_sites_with_paid_plan_having_special_flag(self):
		"""
		If you enable `skip_sites_with_paid_plan` flag, drip emails should not be sent to sites with paid plan set
		No matter whether they have paid for any invoice or not
		"""
		test_app = create_test_app("wiki", "Wiki")
		test_product_trial = create_test_product_trial(test_app)

		drip_email = create_test_drip_email(
			0, product_trial=test_product_trial.name, skip_sites_with_paid_plan=True
		)

		site1 = create_test_site(
			"site1",
			standby_for_product=test_product_trial.name,
			account_request=create_test_account_request(
				"site1", saas=True, product_trial=test_product_trial.name
			).name,
			plan=self.trial_site_plan.name,
		)
		site1.save()

		site2 = create_test_site(
			"site2",
			standby_for_product=test_product_trial.name,
			account_request=create_test_account_request(
				"site2", saas=True, product_trial=test_product_trial.name
			).name,
			plan=self.paid_site_plan.name,
		)
		site2.save()

		site3 = create_test_site(
			"site3",
			standby_for_product=test_product_trial.name,
			account_request=create_test_account_request(
				"site3", saas=True, product_trial=test_product_trial.name
			).name,
			plan=self.trial_site_plan.name,
		)
		site3.save()

		self.assertEqual(drip_email.sites_to_send_drip, [site1.name, site3.name])

	def test_welcome_mail_is_sent_for_new_signups(self):
		from press.press.doctype.drip_email.drip_email import DripEmail, send_welcome_email

		test_app = create_test_app("wiki", "Wiki")
		test_product_trial = create_test_product_trial(test_app)
		create_test_drip_email(
			0, product_trial=test_product_trial.name, skip_sites_with_paid_plan=True, email_type="Sign Up"
		)

		site1 = create_test_site(
			"site1",
			standby_for_product=test_product_trial.name,
			account_request=create_test_account_request(
				"site1", saas=True, product_trial=test_product_trial.name
			).name,
			plan=self.trial_site_plan.name,
		)
		site1.save()

		with patch.object(
			DripEmail,
			"send",
		) as send_welcome_mail:
			send_welcome_email()

		send_welcome_mail.assert_called()
