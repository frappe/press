# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.database.database import get_query_execution_timeout
from frappe.desk.doctype.system_console.system_console import execute_code
from frappe.tests.utils import FrappeTestCase

from press.access import data_console
from press.access.data_console import PressSystemConsole
from press.install import after_install

REFUSED_QUERIES = {
	"update `tabAgent Job Type` set name = 'x'": "Query must be of SELECT or read-only WITH type.",
	"select 1; select 2": "Run one statement at a time",
	"select * from tabSessions": "tabSessions is not the table of a DocType",
	"select * from `__Auth`": "You cannot read __Auth",
	"select * from information_schema.tables": "You cannot read information_schema",
	"select name from tabUser": "You cannot read every record of User",
	"select * from `tabOAuth Bearer Token`": "You cannot read every record of OAuth Bearer Token",
	"select name from `tabAgent Job`": "Agent Job has fields that you cannot read",
	"select * from `tabUser 2FA Recovery Code`": "You cannot read User 2FA, the parent of User 2FA Recovery Code",
	"select name from `tabAgent Job Type` into outfile '/tmp/x'": "INTO is not allowed in a read-only query",
	"select sleep(5)": "SLEEP is not allowed in a read-only query",
	"select name from `tabAgent Job Type` for update": "UPDATE is not allowed in a read-only query",
	"select 1 --1, (select name from tabUser)\n": "Remove comments from the query",
	"select 'a\\\\', (select name from tabUser), 'b'": "Backslashes are not allowed in the query",
	"select 1 as $$, (select name from tabUser) as x, 2 as $$": "Could not parse the query near $$",
	"select setval(`tabAgent Job Type`, 100)": "SETVAL is not allowed in a read-only query",
	"select nextval(`tabAgent Job Type`)": "NEXTVAL is not allowed in a read-only query",
	"select get_lock('x', 100)": "GET_LOCK is not allowed in a read-only query",
	"select release_all_locks()": "RELEASE_ALL_LOCKS is not allowed in a read-only query",
	"with x as (select 1) delete from `tabAgent Job Type`": "DELETE is not allowed in a read-only query",
	"with x as (select 1) update `tabAgent Job Type` set name = 'x'": "UPDATE is not allowed in a read-only query",
	"select 1 lock in share mode": "LOCK is not allowed in a read-only query",
	"select 1 into @a": "INTO is not allowed in a read-only query",
	"select * from `tabAgent Job Type` into dumpfile '/tmp/x'": "INTO is not allowed in a read-only query",
	"selectx 1": "Start the query with SELECT, WITH or EXPLAIN",
}


def create_user(*roles: str) -> str:
	user = frappe.new_doc("User")
	user.update({"email": frappe.mock("email"), "first_name": "Data", "send_welcome_email": 0})
	for role in roles:
		user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return str(user.name)


def console(query: str, type: str = "SQL", commit: int = 0) -> PressSystemConsole:
	return frappe.get_doc({"doctype": "System Console", "type": type, "console": query, "commit": commit})  # type: ignore[return-value]


class TestDataConsole(FrappeTestCase):
	"""The Press Infrastructure Manager role runs read-only SQL on what it can read, and nothing else."""

	def setUp(self):
		# The console commits and rolls back by itself, which would drop the test users
		self.commit = patch.object(frappe.db, "commit").start()
		self.rollback = patch.object(frappe.db, "rollback").start()
		self.switch_to("Press Support L1", "Press Infrastructure Manager")

	def tearDown(self):
		patch.stopall()
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def switch_to(self, *roles: str):
		frappe.set_user("Administrator")
		frappe.set_user(create_user(*roles))

	def assert_refused(self, query: str, message: str, type: str = "SQL"):
		with self.assertRaises(frappe.PermissionError) as raised:
			console(query, type).run()
		self.assertIn(message, str(raised.exception))

	def test_data_console_role_reads_doctype_that_it_can_read(self):
		self.assertIsInstance(console("select 1"), PressSystemConsole)
		result = execute_code(
			json.dumps({"doctype": "System Console", "type": "SQL", "console": "select 'yes' as ok"})
		)
		self.assertEqual(json.loads(result["output"]), [{"ok": "yes"}])
		ran = console("select count(*) as total from `tabAgent Job Type`")
		ran.run()
		self.assertIn("total", json.loads(ran.output or "")[0])

	def test_data_console_rolls_back_and_ignores_commit_flag(self):
		ran = console("select name from `tabAgent Job Type`", commit=1)
		ran.run()
		self.assertFalse(ran.commit)
		self.rollback.assert_called()
		log = frappe.get_last_doc("Console Log")
		self.assertEqual((log.owner, log.get("committed"), log.get("type")), (frappe.session.user, 0, "SQL"))

	def test_data_console_role_explains_a_select(self):
		ran = console("explain select name from `tabAgent Job Type`")
		ran.run()
		self.assertIn("select_type", json.loads(ran.output or "")[0])

	@patch.object(data_console, "MAX_ROWS", 2)
	def test_data_console_shows_at_most_max_rows_and_says_so(self):
		ran = console("select 1 as n union all select 2 union all select 3")
		ran.run()
		rows, note = (ran.output or "").split("\n\n")
		self.assertEqual(json.loads(rows), [{"n": 1}, {"n": 2}])
		self.assertEqual(note, "Showing the first 2 of 3 rows")

	def test_data_console_does_not_add_a_note_when_rows_fit(self):
		ran = console("select 1 as n union all select 2")
		ran.run()
		self.assertEqual(json.loads(ran.output or ""), [{"n": 1}, {"n": 2}])

	def test_data_console_sets_a_statement_timeout_and_resets_it_afterwards(self):
		timeout = patch.object(
			frappe.db, "set_execution_timeout", wraps=frappe.db.set_execution_timeout
		).start()
		console("select 1").run()
		calls = [call.args[0] for call in timeout.call_args_list]
		self.assertEqual(calls, [data_console.STATEMENT_TIMEOUT, get_query_execution_timeout()])
		session_timeout = frappe.db.sql("select @@session.max_statement_time", pluck=True)
		self.assertEqual(session_timeout, [get_query_execution_timeout()])

	def test_data_console_resets_the_statement_timeout_when_the_query_fails(self):
		timeout = patch.object(
			frappe.db, "set_execution_timeout", wraps=frappe.db.set_execution_timeout
		).start()
		ran = console("select no_such_column from `tabAgent Job Type`")
		ran.run()
		self.assertIn("no_such_column", ran.output or "")
		self.assertEqual(timeout.call_args_list[-1].args, (get_query_execution_timeout(),))

	def test_data_console_role_cannot_run_python(self):
		self.assert_refused(
			"frappe.db.sql('delete from tabUser')",
			"The Press Infrastructure Manager role can run SQL only",
			"Python",
		)

	def test_data_console_refuses_writes_system_tables_and_unreadable_doctypes(self):
		for query, message in REFUSED_QUERIES.items():
			with self.subTest(query=query):
				self.assert_refused(query, message)

	def test_refused_query_is_still_logged(self):
		self.assert_refused("select * from `__Auth`", "You cannot read __Auth")
		self.assertEqual(frappe.get_last_doc("Console Log").get("script"), "select * from `__Auth`")

	def test_user_without_data_console_role_cannot_run_sql(self):
		self.switch_to("Press Support L1")
		self.assert_refused("select 1", "You need the System Manager role to use the System Console")

	def test_system_manager_is_not_limited_by_the_sql_guard(self):
		self.switch_to("System Manager")
		ran = console("select count(*) as total from `__Auth`")
		ran.run()
		self.assertIn("total", json.loads(ran.output or "")[0])


def clear_console_meta():
	# A bare clear_cache keeps the DocType meta, which holds the permission rules
	for doctype in ("System Console", "Console Log"):
		frappe.clear_cache(doctype=doctype)


class TestDataConsoleInstall(FrappeTestCase):
	"""A fresh install marks patches as done without running them, so after_install sets up the rules."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		clear_console_meta()

	@patch("press.install.create_default_cluster", new=lambda: None)
	@patch("press.install.create_administrator_team", new=lambda: None)
	def test_after_install_lets_data_console_role_write_system_console_and_read_console_logs(self):
		frappe.db.delete("Custom DocPerm", {"role": "Press Infrastructure Manager"})
		clear_console_meta()
		user = create_user("Press Infrastructure Manager")
		self.assertFalse(frappe.has_permission("System Console", "write", user=user))
		after_install()
		clear_console_meta()
		self.assertTrue(frappe.has_permission("System Console", "write", user=user))
		self.assertTrue(frappe.has_permission("Console Log", "read", user=user))
