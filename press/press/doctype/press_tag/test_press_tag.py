# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from press.press.doctype.team.test_team import create_test_team


def create_and_add_test_tag(name: str, doctype: str, tag: str = "test_tag"):
	test_tag = frappe.get_doc(
		{
			"doctype": "Press Tag",
			"doctype_name": doctype,
			"team": create_test_team().name,
			"tag": tag,
		}
	).insert(ignore_permissions=True)
	doc = frappe.get_doc(doctype, name).append("tags", {"tag": test_tag.name})
	doc.save()
	return test_tag


class TestPressTag(IntegrationTestCase):
	pass
