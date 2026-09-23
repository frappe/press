from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.press_settings.press_settings import PressSettings
from press.press.doctype.site.backups import (
	ScheduledBackupJob,
	get_sites_without_offsite_backups,
	schedule_logical_backups_for_sites_with_backup_time,
	schedule_physical_backups_for_sites_with_backup_time,
)
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.subscription.subscription import Subscription


@patch("press.press.doctype.site.backups.frappe.db.commit", new=MagicMock)
@patch("press.press.doctype.site.backups.frappe.db.rollback", new=MagicMock)
@patch.object(AgentJob, "after_insert", new=Mock())
class TestScheduledBackupJob(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _offsite_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "offsite": True})

	def _with_files_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "with_files": True})

	def setUp(self):
		super().setUp()

		self.interval = 6
		frappe.db.set_single_value("Press Settings", "backup_interval", 6)

	def _interval_hrs_ago(self):
		return frappe.utils.now_datetime() - timedelta(hours=self.interval)

	def _create_site_requiring_backup(self, **kwargs):
		return create_test_site(creation=self._interval_hrs_ago() - timedelta(hours=1), **kwargs)

	@patch.object(
		ScheduledBackupJob,
		"is_backup_hour",
		new=lambda self, x: True,  # always backup hour
	)
	@patch.object(
		ScheduledBackupJob,
		"take_offsite",
		new=lambda self, x, y: True,  # take offsite anyway
	)
	def test_offsite_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob(backup_type="Logical")

		offsite_count_before = self._offsite_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._offsite_count(site.name)
		job = ScheduledBackupJob(backup_type="Logical")
		job.start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	@patch.object(
		ScheduledBackupJob,
		"is_backup_hour",
		new=lambda self, x: True,  # always backup hour
	)
	def test_with_files_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob(backup_type="Logical")

		offsite_count_before = self._with_files_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._with_files_count(site.name)
		job = ScheduledBackupJob(backup_type="Logical")
		job.start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	def _create_x_sites_on_1_bench(self, x):
		site = self._create_site_requiring_backup()
		bench = site.bench
		for _i in range(x - 1):
			self._create_site_requiring_backup(bench=bench)

	def test_limit_number_of_sites_backed_up(self):
		self._create_x_sites_on_1_bench(1)
		self._create_x_sites_on_1_bench(2)
		limit = 3

		job = ScheduledBackupJob(backup_type="Logical")
		sites_num_old = len(job.sites)

		job.limit = limit
		job.start()
		sites_for_backup = [site.name for site in job.sites]
		frappe.db.set_value(
			"Site Backup",
			{"site": ("in", sites_for_backup)},
			"status",
			"Success",  # fake succesful backup
		)

		job = ScheduledBackupJob(backup_type="Logical")
		sites_num_new = len(job.sites)

		self.assertLess(sites_num_new, sites_num_old)
		self.assertEqual(sites_num_old - sites_num_new, limit)

	def test_sites_considered_for_backup(self):
		"""Ensure sites with succesful or pending backups in past interval are skipped."""
		sites = Site.get_sites_for_backup(self.interval)
		self.assertEqual(sites, [])

		site_1 = self._create_site_requiring_backup()
		create_test_site_backup(site_1.name, status="Pending")
		site_2 = self._create_site_requiring_backup()
		create_test_site_backup(site_2.name, status="Failure")
		site_3 = self._create_site_requiring_backup()
		create_test_site_backup(site_3.name, status="Success")
		site_4 = self._create_site_requiring_backup()
		create_test_site_backup(site_4.name, status="Running")

		sites = Site.get_sites_for_backup(self.interval)
		self.assertEqual(len(sites), 1)

		sites_for_backup = [site.name for site in sites]
		self.assertIn(site_2.name, sites_for_backup)

	@patch.object(Site, "backup")
	def test_site_with_logical_backup_time_taken_at_right_time(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.schedule_logical_backup_at_custom_time = True
		site.append(
			"logical_backup_times",
			{
				"backup_time": "00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 01:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		job = ScheduledBackupJob(backup_type="Logical")
		self.assertEqual(len(job.sites), 0)  # site with backup time should be skipped

	@patch.object(Site, "backup")
	def test_site_with_physical_backup_time_taken_at_right_time(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.skip_scheduled_physical_backups = False
		site.schedule_physical_backup_at_custom_time = True
		site.append(
			"physical_backup_times",
			{
				"backup_time": "00:00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 01:00"):
			schedule_physical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_physical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		print(mock_backup.call_args)
		job = ScheduledBackupJob(backup_type="Physical")
		self.assertEqual(len(job.sites), 0)  # site with backup time should be skipped

	@patch.object(Site, "backup")
	def test_site_with_multiple_logical_backup_times(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.schedule_logical_backup_at_custom_time = True
		site.append(
			"logical_backup_times",
			{
				"backup_time": "01:00:00",
			},
		)
		site.append(
			"logical_backup_times",
			{
				"backup_time": "05:00:00",
			},
		)
		site.append(
			"logical_backup_times",
			{
				"backup_time": "12:00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 01:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()

		with self.freeze_time("2021-01-01 02:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 03:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 04:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 05:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()

		with self.freeze_time("2021-01-01 06:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 12:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()

	def _create_site_with_backup_times(self, *times: str) -> Site:
		site: Site = create_test_site()
		site.schedule_logical_backup_at_custom_time = True
		for backup_time in times:
			site.append("logical_backup_times", {"backup_time": backup_time})
		site.save()
		return site

	def test_custom_time_backup_is_not_offsite_on_a_plan_without_offsite_backups(self):
		site = self._create_site_with_backup_times("00:00")

		with (
			patch.object(PressSettings, "is_offsite_setup", return_value=True),
			patch.object(Subscription, "get_sites_without_offsite_backups", return_value=[site.name]),
			self.freeze_time("2021-01-01 00:00"),
		):
			schedule_logical_backups_for_sites_with_backup_time()

		self.assertEqual(self._offsite_count(site.name), 0)
		self.assertEqual(frappe.db.count("Site Backup", {"site": site.name}), 1)

	def test_custom_time_backup_is_not_offsite_when_the_site_turned_offsite_off(self):
		site = self._create_site_with_backup_times("00:00")
		site.update_offsite_backups(enabled=False)

		with (
			patch.object(PressSettings, "is_offsite_setup", return_value=True),
			patch.object(Subscription, "get_sites_without_offsite_backups", return_value=[]),
			self.freeze_time("2021-01-01 00:00"),
		):
			schedule_logical_backups_for_sites_with_backup_time()

		self.assertEqual(self._offsite_count(site.name), 0)
		self.assertEqual(frappe.db.count("Site Backup", {"site": site.name}), 1)

	def test_a_site_that_turned_offsite_off_is_left_out_of_the_offsite_backups(self):
		site = create_test_site()
		site.update_offsite_backups(enabled=False)

		with patch.object(Subscription, "get_sites_without_offsite_backups", return_value=[]):
			self.assertIn(site.name, get_sites_without_offsite_backups())

	def test_custom_time_backups_go_offsite_only_once_a_day(self):
		site = self._create_site_with_backup_times("00:00", "01:00")

		with (
			patch.object(PressSettings, "is_offsite_setup", return_value=True),
			patch.object(Subscription, "get_sites_without_offsite_backups", return_value=[]),
		):
			with self.freeze_time("2021-01-01 00:00"):
				schedule_logical_backups_for_sites_with_backup_time()
			frappe.get_last_doc("Site Backup", {"site": site.name}).db_set("status", "Success")
			with self.freeze_time("2021-01-01 01:00"):
				schedule_logical_backups_for_sites_with_backup_time()

		self.assertEqual(self._offsite_count(site.name), 1)
		self.assertEqual(frappe.db.count("Site Backup", {"site": site.name}), 2)


@patch.object(AgentJob, "after_insert", new=Mock())
class TestBackupSchedule(FrappeTestCase):
	"""The backup schedule as the dashboard reads and writes it."""

	def tearDown(self):
		frappe.db.rollback()

	def _create_site(self, price_usd: float = 25.0, offsite_backups: bool = True) -> Site:
		plan = create_test_plan(
			"Site",
			plan_name=f"Test Site Plan USD {price_usd}{' with offsite backups' if offsite_backups else ''}",
			price_usd=price_usd,
			offsite_backups=offsite_backups,
		)
		return create_test_site(plan=plan.name)

	def test_setting_a_backup_time_takes_the_site_off_the_default_schedule(self):
		site = self._create_site()

		site.update_backup_schedule("02:00")

		site.reload()
		self.assertEqual(
			site.get_backup_schedule(),
			{
				"custom": True,
				"times": ["02:00"],
				"can_set_time": True,
				"can_set_offsite": True,
				"offsite": True,
			},
		)
		self.assertNotIn(site.name, [s.name for s in Site.get_sites_for_backup(6)])

	def test_clearing_the_backup_time_returns_the_site_to_the_default_schedule(self):
		site = self._create_site()
		site.update_backup_schedule("02:00")
		site.reload()

		site.update_backup_schedule(None)

		site.reload()
		self.assertEqual(
			site.get_backup_schedule(),
			{
				"custom": False,
				"times": [],
				"can_set_time": True,
				"can_set_offsite": True,
				"offsite": True,
			},
		)

	def test_the_dashboard_cannot_change_the_backup_times_we_set_up(self):
		site = self._create_site()
		for backup_time in ("02:00:00", "08:00:00"):
			site.append("logical_backup_times", {"backup_time": backup_time})
		site.schedule_logical_backup_at_custom_time = True
		site.save()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Write to support",
			site.update_backup_schedule,
			"14:00",
		)
		site.reload()
		self.assertEqual(
			site.get_backup_schedule(),
			{
				"custom": True,
				"times": ["02:00", "08:00"],
				"can_set_time": True,
				"can_set_offsite": True,
				"offsite": True,
			},
		)

	def test_backup_schedule_rejects_a_time_that_is_not_hh_mm(self):
		site = self._create_site()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"not a valid backup time",
			site.update_backup_schedule,
			"2 AM",
		)

	def test_backup_schedule_is_not_offered_below_the_cutoff_price(self):
		site = self._create_site(price_usd=10.0)

		self.assertFalse(site.plan_allows_backup_schedule())
		self.assertRaisesRegex(
			frappe.ValidationError,
			"does not come with a backup schedule",
			site.update_backup_schedule,
			"02:00",
		)

	def test_backup_schedule_is_offered_on_enterprise_plans_priced_at_zero(self):
		site = self._create_site(price_usd=0.0)

		self.assertTrue(site.plan_allows_backup_schedule())

	def test_backup_schedule_is_not_offered_on_plans_without_offsite_backups(self):
		site = self._create_site(price_usd=0.0, offsite_backups=False)

		self.assertFalse(site.plan_allows_backup_schedule())

	def test_offsite_backups_stay_on_until_the_site_turns_them_off(self):
		site = self._create_site()

		self.assertTrue(site.get_backup_schedule()["offsite"])

		site.update_offsite_backups(enabled=False)

		site.reload()
		self.assertTrue(site.skip_offsite_backups)
		self.assertFalse(site.get_backup_schedule()["offsite"])

	def test_offsite_backups_can_be_turned_back_on(self):
		site = self._create_site()
		site.update_offsite_backups(enabled=False)
		site.reload()

		site.update_offsite_backups(enabled=True)

		site.reload()
		self.assertFalse(site.skip_offsite_backups)
		self.assertTrue(site.get_backup_schedule()["offsite"])

	def test_the_switch_is_offered_to_a_site_the_scheduler_sends_offsite(self):
		site = self._create_site()

		self.assertTrue(site.offsite_backups_available())
		self.assertTrue(site.get_backup_schedule()["can_set_offsite"])

	def test_the_switch_is_withheld_when_the_subscription_plan_has_no_offsite_backups(self):
		"""The scheduler drops a site by its subscription, so the switch has to read that too."""
		site = self._create_site()
		plan_without_offsite = create_test_plan("Site", plan_name="Test No Offsite", offsite_backups=False)
		frappe.get_doc(
			{
				"doctype": "Subscription",
				"team": site.team,
				"document_type": "Site",
				"document_name": site.name,
				"plan_type": "Site Plan",
				"plan": plan_without_offsite.name,
			}
		).insert(ignore_permissions=True)

		self.assertFalse(site.offsite_backups_available())
		self.assertRaisesRegex(
			frappe.ValidationError,
			"takes no offsite backups",
			site.update_offsite_backups,
			enabled=True,
		)

	def test_a_site_without_a_subscription_keeps_its_offsite_backups(self):
		"""`Subscription.get_sites_without_offsite_backups` never names such a site."""
		site = self._create_site()

		self.assertFalse(frappe.db.exists("Subscription", {"document_name": site.name}))
		self.assertTrue(site.offsite_backups_available())
