from unittest.mock import patch, Mock
import frappe
from press.api.saas import account_request
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.test_site import create_test_bench

from press.press.doctype.team.test_team import create_test_press_admin_team

from frappe.tests.utils import FrappeTestCase

from press.saas.doctype.saas_settings.test_saas_settings import (
	create_test_saas_settings,
)


@patch(
	"press.press.doctype.account_request.account_request.frappe.sendmail", new=Mock()
)
class TestAPISaas(FrappeTestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.group = create_test_release_group([create_test_app()])
		create_test_bench(group=self.group)

	def tearDown(self):
		frappe.db.rollback()

	def test_saas_site_is_created_on_account_request_when_pool_isnt_there(self):
		"""
		Tests that a site is created when account_request is called
		"""
		app = create_test_app()
		create_test_marketplace_app(app.name)
		create_test_saas_settings(group=self.group)
		account_request(
			subdomain="test2",
			email=frappe.mock("email"),
			password=frappe.mock("email"),
			first_name="Test",
			last_name="User",
			country="India",
			app=app.name,
		)
		self.assertTrue(frappe.db.exists("Site", "test2.fc.dev"))
		site = frappe.get_doc("Site", "test2.fc.dev")
		self.assertTrue(site.standby_for, "frappe")  # frappe is default saas app
