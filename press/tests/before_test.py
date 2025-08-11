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
	frappe.db.truncate("Agent Request Failure")
	frappe.local.conf.update({"throttle_user_limit": 600})


def execute():
	settings = frappe.get_single("Press Settings")
	if not (settings.stripe_secret_key and settings.stripe_publishable_key):
		create_test_stripe_credentials()
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
		from datetime import UTC
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
