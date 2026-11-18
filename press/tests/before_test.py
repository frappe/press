# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import os
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import set_user as _set_user
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase

from press.utils import _get_current_team, _system_user


def doc_equal(self: Document, other: Document) -> bool:
	"""Partial equality checking of Document object"""
	if not isinstance(other, Document):
		return False
	if self.doctype == other.doctype and self.name == other.name:
		return True
	return False


def FrappeTestCase_setUp(self) -> None:
	frappe.clear_cache()
	self.SHOW_TRANSACTION_COMMIT_WARNINGS = False
	frappe.db.truncate("Agent Request Failure")
	self.SHOW_TRANSACTION_COMMIT_WARNINGS = True
	frappe.local.conf.update({"throttle_user_limit": 600})


def execute():
	settings = frappe.get_single("Press Settings")
	if not (settings.stripe_secret_key and settings.stripe_publishable_key):
		create_test_stripe_credentials()
	set_test_backup_bucket_on_clusters()
	set_test_offsite_backup_credentials()
	import cssutils

	# Silence the cssutils errors that are mostly pointless
	cssutils.log.setLevel(50)

	# Monkey patch certain methods for when tests are running
	Document.__eq__ = doc_equal

	FrappeTestCase.setUp = FrappeTestCase_setUp
	FrappeTestCase.tearDown = lambda self: frappe.db.rollback()
	FrappeTestCase.freeze_time = staticmethod(freeze_time)

	# patch frappe.set_user that
	frappe.set_user = set_user_with_current_team

	# frappe.local.team helper
	frappe.local.team = _get_current_team
	frappe.local.system_user = _system_user


def set_user_with_current_team(user):
	_set_user(user)
	frappe.local._current_team = None


def set_test_backup_bucket_on_clusters():
	"""Clusters made without a bucket, such as Default at install, cannot take offsite backups."""
	from press.press.doctype.backup_bucket.test_backup_bucket import create_test_backup_bucket

	without_bucket = {"backup_bucket": ("is", "not set")}
	if not frappe.db.exists("Cluster", without_bucket):
		return

	bucket = create_test_backup_bucket("default.backups.test").name
	frappe.db.set_value("Cluster", without_bucket, "backup_bucket", bucket)
	# Each test rolls back, so the fixture must be committed to last
	frappe.db.commit()  # nosemgrep


def set_test_offsite_backup_credentials():
	"""A cluster with a bucket sends offsite credentials to the agent."""
	from press.press.doctype.press_settings.press_settings import PressSettings

	settings = PressSettings("Press Settings", "Press Settings")
	if settings.offsite_backups_access_key_id:
		return

	settings.offsite_backups_access_key_id = "test"
	settings.offsite_backups_secret_access_key = frappe.mock("password")
	# A fresh test site has no certbot directory or EFF email, which are mandatory
	settings.flags.ignore_mandatory = True
	settings.save()
	frappe.db.commit()  # nosemgrep


def create_test_stripe_credentials():
	publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY")
	secret_key = os.environ.get("STRIPE_SECRET_KEY")

	if publishable_key and secret_key:
		frappe.db.set_single_value("Press Settings", "stripe_publishable_key", publishable_key)
		frappe.db.set_single_value("Press Settings", "stripe_secret_key", secret_key)


@contextmanager
def freeze_time(time_to_freeze: Any, is_utc: bool = False, *args: Any, **kwargs: Any):
	"""freeze time using freezegun, compatible with Python 3.10 and 3.11+."""
	try:
		from datetime import UTC  # type: ignore
	except ImportError:
		from datetime import timezone

		UTC = timezone.utc

	from zoneinfo import ZoneInfo

	from frappe.utils.data import get_datetime, get_system_timezone
	from freezegun import freeze_time as freezegun_freeze_time

	if not is_utc:
		time_to_freeze = (
			get_datetime(time_to_freeze).replace(tzinfo=ZoneInfo(get_system_timezone())).astimezone(UTC)
		)

	with freezegun_freeze_time(time_to_freeze, *args, **kwargs):
		yield
