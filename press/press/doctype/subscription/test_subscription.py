# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.subscription.subscription import Subscription, sites_with_free_hosting
from press.press.doctype.team.test_team import create_test_team


def create_test_subscription(
	document_name: str,
	plan: str,
	team: str,
	document_type: str = "Site",
	plan_type: str = "Site Plan",
):
	subscription = frappe.get_doc(
		{
			"doctype": "Subscription",
			"document_type": document_type,
			"document_name": document_name,
			"team": team,
			"plan_type": plan_type,
			"plan": plan,
			"site": document_name if document_type == "Site" else None,
		}
	).insert(ignore_if_duplicate=True)
	subscription.reload()
	return subscription


class TestSubscription(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()
		frappe.set_user(self.team.user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_subscription_daily(self):
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan_type="Site Plan",
			plan=plan.name,
		).insert()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)
		desired_value = plan.get_price_per_day("INR") * 2

		is_last_day_of_month = frappe.utils.data.get_last_day(today) == today
		yesterday = frappe.utils.add_days(today, -1)

		# Consider yesterday's and today's record instead of today and tomorrow
		# Became flaky if it was last day of month because
		# tomorrow went outside of this month's invoice's period
		if is_last_day_of_month:
			tomorrow = today
			today = yesterday

		with patch.object(frappe.utils, "today", return_value=today):
			subscription.create_usage_record()
			# this should not create duplicate record
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": self.team.name, "status": "Draft"})
		self.assertEqual(invoice.total, desired_value)

	def test_subscription_for_non_chargeable_document(self):
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan_type="Site Plan",
			plan=plan.name,
		).insert()

		def method(_subscription):
			return False

		# subscription calls this method when checking if it should create a usage record
		todo.can_charge_for_subscription = method

		with patch.object(subscription, "get_subscribed_document", return_value=todo):
			# shouldn't create a usage record
			usage_record = subscription.create_usage_record()
			self.assertTrue(usage_record is None)

	def test_site_in_trial(self):
		self.team.create_upcoming_invoice()

		two_days_after = frappe.utils.add_days(None, 2)
		site = create_test_site()
		site.trial_end_date = two_days_after
		site.save()

		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="Site",
			interval="Daily",
			price_usd=30,
			price_inr=30,
			period=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="Site",
			document_name=site.name,
			plan_type="Site Plan",
			plan=plan.name,
		).insert()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)

		with patch.object(frappe.utils, "today", return_value=today):
			# shouldn't create a usage record as site is in trial
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			# shouldn't create a usage record as site is in trial
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": self.team.name, "status": "Draft"})
		self.assertEqual(invoice.total, 0)

	def test_sites_with_free_hosting(self):
		self.team.create_upcoming_invoice()

		site1 = create_test_site(team=self.team.name)
		site1.free = 1
		site1.save()
		create_test_site(team=self.team.name)

		# test: site marked as free
		free_sites = sites_with_free_hosting()
		self.assertEqual(len(free_sites), 1)

		self.team.free_account = True
		self.team.save()

		# test: site owned by free account
		free_sites = sites_with_free_hosting()
		self.assertEqual(len(free_sites), 2)


class TestIsValidSubscription(FrappeTestCase):
	"""Tests for is_valid_subscription — the date guard used before every billing call.

	create_usage_record calls this before creating charges; if the check is
	broken (e.g. comparison flipped), subscriptions would be billed for dates
	before they existed.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()

		self.plan = frappe.get_doc(
			doctype="Site Plan",
			name="ValidCheck-Plan",
			document_type="ToDo",
			interval="Daily",
			price_usd=10,
			price_inr=10,
		).insert()

		self.todo = frappe.get_doc(doctype="ToDo", description="ValidCheck todo").insert()
		self.subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=self.todo.name,
			plan_type="Site Plan",
			plan=self.plan.name,
		).insert()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_subscription_is_valid_for_today_and_future_dates(self):
		today = frappe.utils.getdate()
		self.assertTrue(self.subscription.is_valid_subscription(today))
		tomorrow = frappe.utils.add_days(today, 1)
		self.assertTrue(self.subscription.is_valid_subscription(tomorrow))

	def test_subscription_is_invalid_for_dates_before_creation(self):
		# creation is set to today; billing for yesterday must be rejected
		yesterday = frappe.utils.add_days(frappe.utils.getdate(), -1)
		self.assertFalse(self.subscription.is_valid_subscription(yesterday))


class TestSubscriptionValidateDuplicate(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.plan = frappe.get_doc(
			doctype="Site Plan",
			name="DupCheck-Plan",
			document_type="ToDo",
			interval="Daily",
			price_usd=10,
			price_inr=10,
		).insert()
		self.todo = frappe.get_doc(doctype="ToDo", description="Dup check todo").insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_duplicate_subscription_raises_error(self):
		frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=self.todo.name,
			plan_type="Site Plan",
			plan=self.plan.name,
		).insert()

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				doctype="Subscription",
				team=self.team.name,
				document_type="ToDo",
				document_name=self.todo.name,
				plan_type="Site Plan",
				plan=self.plan.name,
			).insert()

	def test_subscription_for_different_document_does_not_raise(self):
		frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=self.todo.name,
			plan_type="Site Plan",
			plan=self.plan.name,
		).insert()

		other_todo = frappe.get_doc(doctype="ToDo", description="Other todo").insert()
		# Different document_name — should succeed without raising
		other_sub = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=other_todo.name,
			plan_type="Site Plan",
			plan=self.plan.name,
		).insert()
		self.assertIsNotNone(other_sub.name)


class TestDailyUsageRecordDeduplication(FrappeTestCase):
	"""The billing scheduler calls create_usage_record() for every active
	subscription each night.  A broken deduplication guard would silently
	double-charge every customer overnight — one of the highest-impact billing
	bugs possible.

	All real site/server subscriptions use interval="Daily" (one record per day),
	so this is the production code path that matters.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()
		frappe.set_user(self.team.user)
		self.team.create_upcoming_invoice()

		self.plan = frappe.get_doc(
			doctype="Site Plan",
			name="DailyDedup-Plan",
			document_type="Site",
			interval="Daily",
			price_usd=10,
			price_inr=10,
			period=30,
		).insert()
		self.site = create_test_site(team=self.team.name)
		self.subscription = create_test_subscription(
			document_name=self.site.name,
			plan=self.plan.name,
			team=self.team.name,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_second_call_same_day_returns_none(self):
		today = frappe.utils.getdate()
		first = self.subscription.create_usage_record(date=today)
		second = self.subscription.create_usage_record(date=today)

		self.assertIsNotNone(first)
		self.assertIsNone(second)  # guard must block the duplicate

	def test_each_day_creates_its_own_record(self):
		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)
		self.subscription.create_usage_record(date=today)
		self.subscription.create_usage_record(date=tomorrow)

		records = frappe.get_all("Usage Record", filters={"subscription": self.subscription.name})
		self.assertEqual(len(records), 2)


class TestSecondaryServerNotCharged(FrappeTestCase):
	"""Secondary *application* servers (document_type="Server") must not be billed.

	A cluster can have one primary application server and one or more
	secondary application servers sharing the same bench.  The is_primary
	guard in create_usage_record() prevents double-charging for those secondaries.

	Note: Database Server replicas use document_type="Database Server" and
	are intentionally charged separately — this guard does not apply to them.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.team.allocate_credit_amount(500, source="Prepaid Credits")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()
		frappe.set_user(self.team.user)
		self.team.create_upcoming_invoice()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _server_subscription(self) -> Subscription:
		"""Insert a Server-type subscription with fake document_name and plan.

		ignore_links skips FK validation (the fake names don't exist in DB).
		on_update is patched to prevent Frappe loading the non-existent Server doc.
		"""
		with patch.object(Subscription, "on_update"):
			return frappe.get_doc(
				doctype="Subscription",
				team=self.team.name,
				document_type="Server",
				document_name="test-server.frappe.cloud",
				plan_type="Server Plan",
				plan="stub-plan",
			).insert(ignore_links=True)

	def _mock_get_cached_doc(self, mock_plan):
		"""Return a side_effect for frappe.get_cached_doc that serves a stub Team
		and a stub plan while letting other calls fail loudly."""
		real_team = self.team

		def _side_effect(doctype, name):
			if doctype == "Team":
				return real_team
			if doctype == "Server Plan":
				return mock_plan
			raise AssertionError(f"Unexpected get_cached_doc({doctype!r}, {name!r})")

		return _side_effect

	def test_secondary_server_creates_no_usage_record(self):
		sub = self._server_subscription()
		mock_plan = Mock()
		mock_plan.get_price_for_interval.return_value = 100.0

		with (
			patch.object(sub, "can_charge_for_subscription", return_value=True),
			patch.object(sub, "is_usage_record_created", return_value=False),
			patch.object(sub, "is_valid_subscription", return_value=True),
			patch(
				"press.press.doctype.subscription.subscription.frappe.get_cached_doc",
				side_effect=self._mock_get_cached_doc(mock_plan),
			),
			patch.object(frappe.db, "get_value", return_value=0),  # is_primary = False
		):
			result = sub.create_usage_record()

		self.assertIsNone(result)


class TestGetSitesWithoutOffsiteBackups(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()

	def tearDown(self):
		frappe.db.rollback()

	def test_returns_sites_on_plans_without_offsite_backups(self):
		from press.press.doctype.site_plan.site_plan import SitePlan

		with patch.object(SitePlan, "get_ones_without_offsite_backups", return_value=[]):
			sites = Subscription.get_sites_without_offsite_backups()
			self.assertEqual(sites, [])
