# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.model.base_document import BaseDocument
from frappe.tests.test_api import FrappeAPITestCase, make_request
from frappe.utils import get_test_client

from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team

PASSWORD = "Dashboard-Request-Test-1!"  # pragma: allowlist secret


class DashboardRequestTestCase(FrappeAPITestCase):
	"""Send real requests as a Press User, the way the dashboard does.

	Each request runs in its own thread and database connection, so fixtures are
	committed. `tearDown` deletes every row that the test and its requests inserted.
	"""

	def setUp(self):
		self.client = get_test_client()
		self.users: list[str] = []
		self.inserted_rows = record_inserted_rows(self)
		self.email = self.create_press_user()
		self.team = create_test_team(self.email)
		# rate limits count per IP, and every test request comes from 127.0.0.1
		frappe.cache.delete_keys("rl:")
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()
		for doctype, name in reversed(self.inserted_rows):
			delete_row(doctype, name)
		frappe.db.delete("Sessions", {"user": ("in", self.users)})
		frappe.db.commit()
		super().tearDown()

	def create_press_user(self) -> str:
		"""Sign up the way a customer does: the user gets only the Press User role."""
		email = frappe.mock("email")
		Team.create_user(first_name="Dashboard", email=email, password=PASSWORD)
		self.users.append(email)
		return email

	def login(self, email: str | None = None):
		# the dashboard drops the current team on logout, so login sends no team
		response = self.send("login", {"usr": email or self.email, "pwd": PASSWORD})
		self.assertEqual(response.status_code, 200, response.json)

	def post(self, method: str, data: dict | None = None):
		return self.send(method, data, {"X-Press-Team": self.team.name})

	def send(self, method: str, data: dict | None = None, headers: dict | None = None):
		return make_request(
			target=self.client.post,
			args=(f"/api/method/{method}",),
			# buffered closes the response, which runs after_response and saves the session
			kwargs={"json": data or {}, "headers": headers or {}, "buffered": True},
		)

	def run_doc_method(self, doc, method: str, args: dict | None = None):
		return self.post(
			"press.api.client.run_doc_method",
			{"dt": doc.doctype, "dn": doc.name, "method": method, "args": args},
		)

	def assertSucceeded(self, response):
		self.assertEqual(response.status_code, 200, response.json)

	def assertStillLoggedIn(self, email: str | None = None):
		me = self.post("press.api.account.me")
		self.assertEqual(me.status_code, 200, me.json)
		self.assertEqual(me.json["message"]["user"], email or self.email)


def record_inserted_rows(test) -> list[tuple[str, str]]:
	"""Record each new row, in the test thread and in the request threads."""
	rows = []
	db_insert = BaseDocument.db_insert

	def recording_db_insert(doc, *args, **kwargs):
		# a duplicate insert can be ignored, and the row it hits is not ours to delete
		existed = bool(doc.name) and frappe.db.exists(doc.doctype, doc.name)
		db_insert(doc, *args, **kwargs)
		if not existed:
			rows.append((doc.doctype, doc.name))

	patcher = patch.object(BaseDocument, "db_insert", recording_db_insert)
	patcher.start()
	test.addCleanup(patcher.stop)
	return rows


def delete_row(doctype: str, name: str):
	for table in frappe.get_meta(doctype).get_table_fields():
		frappe.db.delete(table.options, {"parent": name, "parenttype": doctype})
	frappe.db.delete(doctype, name)
