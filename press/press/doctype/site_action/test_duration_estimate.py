# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_action.duration_estimate import estimate_duration
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup

ACTION_TYPE = "Move Site To Different Region"
GIGABYTE = 1024 * 1024 * 1024


def create_test_backup(site: str, creation, duration_in_seconds: int, size: int):
	"""Backup of the given total size that took the given time to run."""
	backup = create_test_site_backup(site, creation=creation)
	job = create_test_agent_job(job_type="Backup Site", status="Success")
	frappe.db.set_value("Agent Job", job.name, "duration", timedelta(seconds=duration_in_seconds))
	frappe.db.set_value(
		"Site Backup",
		backup.name,
		{
			"job": job.name,
			"database_size": size // 2,
			"public_size": size // 4,
			"private_size": size // 4,
		},
	)
	return backup


def create_past_migration(site: str, start, duration_in_seconds: int, backup: dict):
	"""A successful Site Action, along with the backup it took while running."""
	create_test_backup(site, add_to_date(start, seconds=60), backup["duration"], backup["size"])
	action = frappe.get_doc(
		{
			"doctype": "Site Action",
			"action_type": ACTION_TYPE,
			"site": site,
			"team": frappe.db.get_value("Site", site, "team"),
			"status": "Success",
			"start": start,
			"end": add_to_date(start, seconds=duration_in_seconds),
			"duration": duration_in_seconds,
		}
	)
	action.db_insert()
	return action


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestDurationEstimate(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site(subdomain="mover").name
		self.other_site = create_test_site(subdomain="movedbefore").name

	def tearDown(self):
		frappe.db.rollback()

	def add_past_migrations(self, durations: list[int], size: int = GIGABYTE):
		start = add_to_date(None, days=-30)
		for duration in durations:
			create_past_migration(self.other_site, start, duration, {"duration": 200, "size": size})
			start = add_to_date(start, days=1)

	def test_estimate_is_none_when_site_has_never_been_backed_up(self):
		self.assertIsNone(estimate_duration(self.site, ACTION_TYPE))

	def test_estimate_is_twice_the_backup_time_without_comparable_migrations(self):
		create_test_backup(self.site, add_to_date(None, days=-1), 300, GIGABYTE)
		self.assertEqual(estimate_duration(self.site, ACTION_TYPE), 600)

	def test_estimate_adds_migration_overhead_to_the_sites_own_backup_time(self):
		create_test_backup(self.site, add_to_date(None, days=-1), 300, GIGABYTE)
		# Each past migration took 900s, of which 200s was its backup
		self.add_past_migrations([900] * 5)
		self.assertEqual(estimate_duration(self.site, ACTION_TYPE), 1000)

	def test_estimate_ignores_a_migration_that_took_absurdly_long(self):
		create_test_backup(self.site, add_to_date(None, days=-1), 300, GIGABYTE)
		self.add_past_migrations([900, 900, 900, 900, 900, 100000])
		self.assertEqual(estimate_duration(self.site, ACTION_TYPE), 1000)

	def test_estimate_ignores_migrations_of_very_differently_sized_sites(self):
		create_test_backup(self.site, add_to_date(None, days=-1), 300, GIGABYTE)
		self.add_past_migrations([900] * 5, size=100 * GIGABYTE)
		self.assertEqual(estimate_duration(self.site, ACTION_TYPE), 600)
