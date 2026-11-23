import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy_candidate.utils import get_build_server_with_least_active_builds
from press.press.doctype.server.test_server import create_test_server


def open_cleanup_job(server: str, status: str = "Running"):
	frappe.get_doc(
		{
			"doctype": "Press Job",
			"job_type": "Trigger Build Server Cleanup",
			"server_type": "Server",
			"server": server,
			"status": status,
		}
	).db_insert()


class TestBuildServerSelection(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Server", {"use_for_build": 1}, "use_for_build", 0)
		self.first = create_test_server(platform="x86_64", use_for_build=True).name
		self.second = create_test_server(platform="x86_64", use_for_build=True).name

	def tearDown(self):
		frappe.db.rollback()

	def test_new_build_skips_server_with_open_cleanup_job(self):
		# Servers come back newest first, so without the filter the picker returns self.second
		open_cleanup_job(self.second)
		open_cleanup_job(self.first, status="Success")

		self.assertEqual(get_build_server_with_least_active_builds("x86_64"), self.first)

	def test_new_build_uses_cleanup_server_when_every_server_is_in_cleanup(self):
		open_cleanup_job(self.first)
		open_cleanup_job(self.second)

		self.assertIn(get_build_server_with_least_active_builds("x86_64"), (self.first, self.second))
