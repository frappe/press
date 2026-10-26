# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from press.press.report.mariadb_slow_queries.mariadb_slow_queries import normalize_query
from press.utils.sql import format_sql

LONG_IN_LIST = ", ".join(f"'name-{i}'" for i in range(6000))
LONG_INSERT = "INSERT INTO t VALUES " + ", ".join(f"({i}, 'x')" for i in range(6000))


class TestFormatSQL(FrappeTestCase):
	def test_format_sql_uppercases_keywords_and_reindents(self):
		self.assertEqual(
			format_sql("select name from tabSite where x = 1"), "SELECT name\nFROM tabSite\nWHERE x = 1"
		)

	def test_format_sql_strips_leading_comment_without_leaving_newline(self):
		self.assertEqual(format_sql("/* frappe */ select 1", strip_comments=True), "SELECT 1")

	def test_format_sql_returns_query_unchanged_when_it_exceeds_sqlparse_token_limit(self):
		self.assertEqual(format_sql(f" {LONG_INSERT} "), LONG_INSERT)


class TestNormalizeQuery(FrappeTestCase):
	def test_normalize_query_replaces_literals_and_collapses_in_list(self):
		self.assertEqual(
			normalize_query("select name from tabSite where team = 'abc' and status in ('Active', 'Broken')"),
			"SELECT name\nFROM tabSite\nWHERE team = ?\n  AND status IN (?)",
		)

	def test_normalize_query_groups_in_lists_longer_than_sqlparse_token_limit(self):
		short = normalize_query("select * from tabFile where name in ('a', 'b') and is_folder = 0")
		long = normalize_query(f"select * from tabFile where name in ({LONG_IN_LIST}) and is_folder = 0")
		self.assertEqual(long, short)

	def test_normalize_query_keeps_subquery_in_list(self):
		self.assertIn("IN\n    (SELECT b", normalize_query("select * from t where a in (select b from u)"))

	def test_normalize_query_returns_query_unchanged_when_it_exceeds_sqlparse_token_limit(self):
		self.assertEqual(normalize_query(LONG_INSERT), LONG_INSERT)
