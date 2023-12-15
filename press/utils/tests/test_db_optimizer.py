# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from frappe.tests.utils import FrappeTestCase

from press.utils.db_optimizer import DBOptimizer, DBTable


class TestDBOptimizer(FrappeTestCase):
	def test_basic_index_existence_analysis(self):
		def possible_indexes(q):
			user = DBTable.from_frappe_ouput(USER_TABLE)
			has_role = DBTable.from_frappe_ouput(HAS_ROLE_TABLE)
			return [
				i.column
				for i in DBOptimizer(
					query=q,
					tables={"tabUser": user, "tabHas Role": has_role},
				).potential_indexes()
			]

		self.assertEqual(
			["modified"],
			possible_indexes("select `name` from `tabUser` order by `modified` desc limit 1"),
		)

		self.assertEqual(
			["full_name"],
			possible_indexes("select `name` from `tabUser` where full_name = 'xyz'"),
		)

		self.assertIn(
			"parent",
			possible_indexes(
				"select `name` from `tabUser` u join `tabHas Role` h on h.parent = u.name"
			),
		)

	def test_suggestion_using_table_stats(self):
		user = DBTable.from_frappe_ouput(USER_TABLE)
		has_role = DBTable.from_frappe_ouput(HAS_ROLE_TABLE)

		tables = {"tabUser": user, "tabHas Role": has_role}
		self.assertEqual(user.total_rows, 92)

		# This should suggest adding api_key as it definitely has highest cardinality.
		optimizer = DBOptimizer(
			query="select name from tabUser where enabled = 1 and api_key = 'xyz'", tables=tables
		)
		self.assertIn("api_key", [i.column for i in optimizer.potential_indexes()])

		index = optimizer.suggest_index()
		self.assertEqual(index.column, "api_key")

		# This should suggest nothing as modified is already indexed
		optimizer = DBOptimizer(
			query="select name from tabUser order by modified asc",
			tables=tables,
		)
		self.assertIsNone(optimizer.suggest_index())

		# This should suggest nothing as modified is already indexed
		optimizer = DBOptimizer(
			query="select name from tabUser u join `tabHas Role` r on r.parent = u.name where r.role='System Manager'",
			tables=tables,
		)
		index = optimizer.suggest_index()
		self.assertEqual(index.column, "role")
		self.assertEqual(index.table, "tabHas Role")


# Table stats extracted using describe-database-table for testing.

USER_TABLE = {
	"table_name": "tabUser",
	"total_rows": 92,
	"schema": [
		{
			"column": "name",
			"type": "varchar(140)",
			"is_nullable": False,
			"default": None,
			"cardinality": 91,
		},
		{"column": "creation", "type": "datetime(6)", "is_nullable": True, "default": None},
		{
			"column": "modified",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
			"cardinality": 91,
		},
		{
			"column": "modified_by",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{"column": "owner", "type": "varchar(140)", "is_nullable": True, "default": None},
		{"column": "docstatus", "type": "int(1)", "is_nullable": False, "default": "0"},
		{"column": "idx", "type": "int(8)", "is_nullable": False, "default": "0"},
		{"column": "enabled", "type": "int(1)", "is_nullable": False, "default": "1"},
		{"column": "email", "type": "varchar(140)", "is_nullable": False, "default": ""},
		{
			"column": "first_name",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 88,
		},
		{
			"column": "reset_password_key",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 84,
		},
		{
			"column": "user_type",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": "System User",
			"cardinality": 2,
		},
		{
			"column": "api_key",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 70,
		},
		{"column": "api_secret", "type": "text", "is_nullable": True, "default": None},
		{"column": "_user_tags", "type": "text", "is_nullable": True, "default": None},
		{"column": "_comments", "type": "text", "is_nullable": True, "default": None},
		{"column": "_assign", "type": "text", "is_nullable": True, "default": None},
		{"column": "_liked_by", "type": "text", "is_nullable": True, "default": None},
	],
	"indexes": [
		{
			"unique": True,
			"cardinality": 91,
			"name": "PRIMARY",
			"sequence": 1,
			"nullable": False,
			"column": "name",
			"type": "BTREE",
		},
		{
			"unique": True,
			"cardinality": 91,
			"name": "username",
			"sequence": 1,
			"nullable": True,
			"column": "username",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 91,
			"name": "modified",
			"sequence": 1,
			"nullable": True,
			"column": "modified",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 91,
			"name": "reset_password_key_index",
			"sequence": 1,
			"nullable": True,
			"column": "reset_password_key",
			"type": "BTREE",
		},
	],
}


HAS_ROLE_TABLE = {
	"table_name": "tabHas Role",
	"total_rows": 96,
	"schema": [
		{
			"column": "name",
			"type": "varchar(140)",
			"is_nullable": "NO",
			"default": None,
			"cardinality": 92,
		},
		{"column": "creation", "type": "datetime(6)", "is_nullable": "YES", "default": None},
		{"column": "modified", "type": "datetime(6)", "is_nullable": "YES", "default": None},
		{
			"column": "modified_by",
			"type": "varchar(140)",
			"is_nullable": "YES",
			"default": None,
		},
		{"column": "owner", "type": "varchar(140)", "is_nullable": "YES", "default": None},
		{"column": "docstatus", "type": "int(1)", "is_nullable": "NO", "default": "0"},
		{"column": "idx", "type": "int(8)", "is_nullable": "NO", "default": "0"},
		{
			"column": "role",
			"type": "varchar(140)",
			"is_nullable": "YES",
			"default": None,
			"cardinality": 78,
		},
		{
			"column": "parent",
			"type": "varchar(140)",
			"is_nullable": "YES",
			"default": None,
			"cardinality": 92,
		},
		{
			"column": "parentfield",
			"type": "varchar(140)",
			"is_nullable": "YES",
			"default": None,
		},
		{
			"column": "parenttype",
			"type": "varchar(140)",
			"is_nullable": "YES",
			"default": None,
		},
	],
	"indexes": [
		{
			"unique": True,
			"cardinality": 92,
			"name": "PRIMARY",
			"sequence": 1,
			"nullable": "",
			"column": "name",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 92,
			"name": "parent",
			"sequence": 1,
			"nullable": "YES",
			"column": "parent",
			"type": "BTREE",
		},
	],
}
