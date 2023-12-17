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

	def test_complex_sub_query_aliases(self):
		"""Check if table identification is correct for subqueries."""

		q = """SELECT *,
					(SELECT COUNT(*) FROM `tabHD Ticket Comment` WHERE `tabHD Ticket Comment`.`reference_ticket`=`tabHD Ticket`.`name`) `count_comment`,
					(SELECT COUNT(*) FROM `tabCommunication` WHERE `tabCommunication`.`reference_doctype`='HD Ticket' AND `tabCommunication`.`reference_name`=`tabHD Ticket`.`name`) `count_msg`,
				FROM `tabHD Ticket`
				WHERE `agent_group`='L2'
				ORDER BY `modified` DESC
				LIMIT 20
			"""
		optimizer = DBOptimizer(query=q)
		optimizer.update_table_data(DBTable.from_frappe_ouput(HD_TICKET_TABLE))
		optimizer.update_table_data(DBTable.from_frappe_ouput(HD_TICKET_COMMENT_TABLE))
		optimizer.update_table_data(DBTable.from_frappe_ouput(COMMUNICATION_TABLE))

		index = optimizer.suggest_index()
		self.assertEqual(index.table, "tabHD Ticket Comment")
		self.assertEqual(index.column, "reference_ticket")


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


HD_TICKET_TABLE = {
	"table_name": "tabHD Ticket",
	"total_rows": 3820,
	"schema": [
		{
			"column": "name",
			"type": "bigint(20)",
			"is_nullable": False,
			"default": None,
			"cardinality": 3529,
		},
		{"column": "creation", "type": "datetime(6)", "is_nullable": True, "default": None},
		{
			"column": "modified",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
			"cardinality": 3529,
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
		{"column": "subject", "type": "varchar(140)", "is_nullable": True, "default": None},
		{"column": "raised_by", "type": "varchar(140)", "is_nullable": True, "default": None},
		{
			"column": "status",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": "Open",
			"cardinality": 8,
		},
		{"column": "priority", "type": "varchar(140)", "is_nullable": True, "default": None},
		{
			"column": "ticket_type",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "agent_group",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": "L1",
			"cardinality": 9,
		},
		{
			"column": "ticket_split_from",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{"column": "description", "type": "longtext", "is_nullable": True, "default": None},
		{"column": "template", "type": "varchar(140)", "is_nullable": True, "default": None},
		{"column": "sla", "type": "varchar(140)", "is_nullable": True, "default": None},
		{
			"column": "response_by",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "response_by_variance",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "agreement_status",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "resolution_by",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "resolution_by_variance",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "service_level_agreement_creation",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "on_hold_since",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "total_hold_time",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "first_response_time",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "first_responded_on",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "avg_response_time",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "resolution_details",
			"type": "longtext",
			"is_nullable": True,
			"default": None,
		},
		{"column": "opening_date", "type": "date", "is_nullable": True, "default": None},
		{"column": "opening_time", "type": "time(6)", "is_nullable": True, "default": None},
		{
			"column": "resolution_date",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "resolution_time",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{
			"column": "user_resolution_time",
			"type": "decimal(21,9)",
			"is_nullable": True,
			"default": None,
		},
		{"column": "contact", "type": "varchar(140)", "is_nullable": True, "default": None},
		{"column": "customer", "type": "varchar(140)", "is_nullable": True, "default": None},
		{
			"column": "email_account",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{"column": "attachment", "type": "text", "is_nullable": True, "default": None},
		{"column": "_user_tags", "type": "text", "is_nullable": True, "default": None},
		{"column": "_comments", "type": "text", "is_nullable": True, "default": None},
		{"column": "_assign", "type": "text", "is_nullable": True, "default": None},
		{"column": "_liked_by", "type": "text", "is_nullable": True, "default": None},
		{"column": "_seen", "type": "text", "is_nullable": True, "default": None},
	],
	"indexes": [
		{
			"unique": True,
			"cardinality": 3529,
			"name": "PRIMARY",
			"sequence": 1,
			"nullable": False,
			"column": "name",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 8,
			"name": "status",
			"sequence": 1,
			"nullable": True,
			"column": "status",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 3529,
			"name": "modified",
			"sequence": 1,
			"nullable": True,
			"column": "modified",
			"type": "BTREE",
		},
	],
}


HD_TICKET_COMMENT_TABLE = {
	"table_name": "tabHD Ticket Comment",
	"total_rows": 2683,
	"schema": [
		{
			"column": "name",
			"type": "varchar(140)",
			"is_nullable": False,
			"default": None,
			"cardinality": 2683,
		},
		{"column": "creation", "type": "datetime(6)", "is_nullable": True, "default": None},
		{
			"column": "modified",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
			"cardinality": 2345,
		},
		{
			"column": "reference_ticket",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 1379,
		},
		{
			"column": "commented_by",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
		},
		{"column": "content", "type": "longtext", "is_nullable": True, "default": None},
		{"column": "is_pinned", "type": "int(1)", "is_nullable": False, "default": "0"},
	],
	"indexes": [
		{
			"unique": True,
			"cardinality": 2345,
			"name": "PRIMARY",
			"sequence": 1,
			"nullable": False,
			"column": "name",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 2345,
			"name": "modified",
			"sequence": 1,
			"nullable": True,
			"column": "modified",
			"type": "BTREE",
		},
	],
}


COMMUNICATION_TABLE = {
	"table_name": "tabCommunication",
	"total_rows": 20727,
	"schema": [
		{
			"column": "name",
			"type": "varchar(140)",
			"is_nullable": False,
			"default": None,
			"cardinality": 19713,
		},
		{"column": "creation", "type": "datetime(6)", "is_nullable": True, "default": None},
		{
			"column": "modified",
			"type": "datetime(6)",
			"is_nullable": True,
			"default": None,
			"cardinality": 19713,
		},
		{
			"column": "reference_doctype",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 1,
		},
		{
			"column": "reference_name",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 3798,
		},
		{
			"column": "reference_owner",
			"type": "varchar(140)",
			"is_nullable": True,
			"default": None,
			"cardinality": 1314,
		},
	],
	"indexes": [
		{
			"unique": True,
			"cardinality": 19713,
			"name": "PRIMARY",
			"sequence": 1,
			"nullable": False,
			"column": "name",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 19713,
			"name": "modified",
			"sequence": 1,
			"nullable": True,
			"column": "modified",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 2,
			"name": "reference_doctype_reference_name_index",
			"sequence": 1,
			"nullable": True,
			"column": "reference_doctype",
			"type": "BTREE",
		},
		{
			"unique": False,
			"cardinality": 9856,
			"name": "reference_doctype_reference_name_index",
			"sequence": 2,
			"nullable": True,
			"column": "reference_name",
			"type": "BTREE",
		},
	],
}
