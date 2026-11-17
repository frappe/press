# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access.test_employee_consent import create_test_employee, grant_site_access
from press.access.utils import is_outside_employee
from press.api.account import can_switch_to_team
from press.api.client import get
from press.api.site import running_jobs
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import get_current_team

NO_SITE_PERMISSION = "You need the 'read' permission on <strong>Site</strong>"


@patch("frappe.sendmail", new=Mock())
class TestDashboardEmployeeAccess(FrappeTestCase):
	"""On the dashboard, every employee gets the access of a customer, whatever their roles."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.employee = create_test_employee("Press Support Engineer")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.flags.error_message = None
		frappe.db.rollback()

	@contextmanager
	def on_dashboard(self, team: str | None = None):
		frappe.set_user(self.employee.user)
		frappe.local._current_team = None
		frappe.local.request = frappe._dict(
			method="POST", headers={"X-Press-Team": team or self.employee.name}
		)
		try:
			yield
		finally:
			del frappe.local.request
			frappe.local._current_team = None

	def assert_cannot_open_site(self):
		with self.on_dashboard(), self.assertRaises(frappe.PermissionError):
			get("Site", self.site.name)
		self.assertIn(NO_SITE_PERMISSION, frappe.flags.error_message)

	def test_employee_on_dashboard_stays_in_own_team_when_header_names_a_customer_team(self):
		with self.on_dashboard(team=self.site.team):
			self.assertEqual(get_current_team(), self.employee.name)

	def test_employee_on_dashboard_cannot_switch_to_a_customer_team(self):
		with self.on_dashboard():
			self.assertFalse(can_switch_to_team(self.site.team))

	def test_employee_on_dashboard_cannot_open_customer_site_without_consent(self):
		self.assert_cannot_open_site()

	def test_system_manager_on_dashboard_cannot_open_customer_site_without_consent(self):
		self.employee = create_test_employee("System Manager")
		self.assert_cannot_open_site()

	def test_employee_on_dashboard_cannot_call_site_endpoint_without_consent(self):
		with self.on_dashboard(), self.assertRaisesRegex(frappe.PermissionError, "Not Permitted"):
			running_jobs(name=self.site.name)

	def test_employee_on_dashboard_calls_site_endpoint_with_consent(self):
		grant_site_access(self.employee, self.site.name)
		with self.on_dashboard():
			self.assertEqual(running_jobs(name=self.site.name), [])

	def test_employee_on_dashboard_opens_customer_site_with_consent_without_domains_tab(self):
		grant_site_access(self.employee, self.site.name)
		with self.on_dashboard():
			site = get("Site", self.site.name)
		self.assertEqual(site.name, self.site.name)
		self.assertFalse(site.tabs_access["Domains"])
		self.assertFalse(site.tabs_access["Backups"])

	def test_system_manager_on_dashboard_sees_domains_tab_with_domains_consent(self):
		self.employee = create_test_employee("System Manager")
		grant_site_access(self.employee, self.site.name, site_domains=1)
		with self.on_dashboard():
			self.assertTrue(get("Site", self.site.name).tabs_access["Domains"])

	def test_system_manager_on_dashboard_cannot_transfer_customer_site_even_with_consent(self):
		self.employee = create_test_employee("System Manager")
		grant_site_access(self.employee, self.site.name)
		with self.on_dashboard(), self.assertRaisesRegex(frappe.PermissionError, "Only team admin"):
			frappe.get_doc("Site", self.site.name).send_change_team_request("x@example.com", "Moving")

	def test_system_manager_on_dashboard_is_an_outside_employee_of_a_customer_team(self):
		self.employee = create_test_employee("System Manager")
		with self.on_dashboard():
			self.assertTrue(is_outside_employee(self.site.team))

	def test_employee_on_dashboard_reads_site_of_own_team_without_consent(self):
		own_site = create_test_site(team=self.employee.name)
		with self.on_dashboard():
			site = get("Site", own_site.name)
		self.assertEqual(site.tabs_access, {})

	def test_employee_in_desk_can_still_switch_to_a_customer_team(self):
		frappe.set_user(self.employee.user)
		self.assertTrue(can_switch_to_team(self.site.team))
