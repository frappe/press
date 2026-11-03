# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import frappe
import frappe.utils
from frappe.tests.utils import FrappeTestCase


def create_test_site_usage(site: str, database: int, public: int, private: int, hours_ago: int = 0):
	usage = frappe.get_doc(
		{"doctype": "Site Usage", "site": site, "database": database, "public": public, "private": private}
	).insert()
	if hours_ago:
		creation = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-hours_ago)
		usage.db_set("creation", creation, update_modified=False)
	return usage


class TestSiteUsage(FrappeTestCase):
	pass
