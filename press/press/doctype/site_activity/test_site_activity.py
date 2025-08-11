# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils import get_current_team

if TYPE_CHECKING:
	from press.press.doctype.site_activity.site_activity import SiteActivity


def create_test_site_activity(site: str, action: str) -> SiteActivity:
	return frappe.get_doc(
		{  # type: ignore
			"doctype": "Site Activity",
			"site": site,
			"action": action,
			"team": get_current_team(),
		}
	).insert()


class TestSiteActivity(FrappeTestCase):
	pass
