import frappe
from frappe.tests.utils import FrappeTestCase

from press.patches.v0_8_0.fix_dashboard_banner_help_urls import execute

HELP_URLS = {
	"https://docs.frappe.io/cloud": "https://docs.frappe.io/cloud",
	"HTTP://example.com": "http://example.com",
	" https://example.com/help ": "https://example.com/help",
	"docs.frappe.io/cloud/sites": "https://docs.frappe.io/cloud/sites",
	"//docs.frappe.io/cloud": "https://docs.frappe.io/cloud",
	"javascript:alert(document.cookie)": None,
	"javascript://docs.frappe.io/%0aalert(1)": None,
	"data:text/html,x": None,
	"/dashboard/billing": None,
	"see the docs": None,
}


class TestFixDashboardBannerHelpUrls(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_patch_adds_https_to_bare_hosts_and_clears_other_help_urls(self):
		banners = {}
		for help_url in HELP_URLS:
			banner = frappe.get_doc({"doctype": "Dashboard Banner", "title": "Help", "is_global": 1}).insert()
			banner.db_set("help_url", help_url)
			banners[banner.name] = help_url
		execute()
		for name, help_url in banners.items():
			with self.subTest(help_url=help_url):
				self.assertEqual(
					frappe.db.get_value("Dashboard Banner", name, "help_url"), HELP_URLS[help_url]
				)
				frappe.get_doc("Dashboard Banner", name).save()
