# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from press.press.doctype.site_activity.site_activity import SiteActivity


def create_test_site_activity(site: str, action: str) -> SiteActivity:
	return frappe.get_doc(
		{  # type: ignore
			"doctype": "Site Activity",
			"site": site,
			"action": action,
			"team": frappe.db.get_value("Site", site, "team"),
		}
	).insert()


class TestSiteActivity(FrappeTestCase):
	pass
