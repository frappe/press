# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
import typing
from frappe.tests.utils import FrappeTestCase
from frappe.model.naming import make_autoname

if typing.TYPE_CHECKING:
	from press.press.doctype.server_plan.server_plan import ServerPlan


def create_test_server_plan(server_type: str = "Server") -> "ServerPlan":
	"""Create test Server Plan doc."""
	server_plan = frappe.get_doc(
		{
			"doctype": "Server Plan",
			"name": make_autoname("SP-.####"),
			"server_type": server_type,
			"title": frappe.mock("name"),
			"price_inr": 1000,
			"price_usd": 200,
			"enabled": 1,
		}
	).insert()
	server_plan.reload()
	return server_plan


class TestServerPlan(FrappeTestCase):
	pass
