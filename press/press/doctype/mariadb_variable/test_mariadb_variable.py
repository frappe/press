# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)


class TestMariaDBVariable(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_set_on_all_servers_sets_on_all_servers(self):

		db_1 = create_test_database_server()
		db_2 = create_test_database_server()
		db_1.add_mariadb_variable("tmp_disk_table_size", "value_int", 1024)
		db_1.add_mariadb_variable("innodb_old_blocks_time", "value_str", "1000")

		variable = frappe.get_doc("MariaDB Variable", "tmp_disk_table_size")  # in fixture
		variable.default_value = "5120"
		variable.save()

		variable.set_on_all_servers()
		db_1.reload()
		db_2.reload()
		self.assertEqual(db_1.mariadb_system_variables[0].value, 5120 * 1024 * 1024)
		self.assertEqual(db_2.mariadb_system_variables[0].value, 5120 * 1024 * 1024)

		variable = frappe.get_doc("MariaDB Variable", "innodb_old_blocks_time")
		variable.default_value = "5000"
		variable.save()

		variable.set_on_all_servers()
		db_1.reload()
		db_2.reload()
		self.assertEqual(db_1.mariadb_system_variables[1].value, "5000")
		self.assertEqual(db_2.mariadb_system_variables[1].value, "5000")

	def test_set_on_server_sets_on_one_server(self):
		db_1 = create_test_database_server()
		db_2 = create_test_database_server()
		db_2.add_mariadb_variable("tmp_disk_table_size", "value_int", 1024)
		db_1.add_mariadb_variable("tmp_disk_table_size", "value_int", 1024)
		db_1.add_mariadb_variable("innodb_old_blocks_time", "value_str", "1000")

		variable = frappe.get_doc("MariaDB Variable", "tmp_disk_table_size")
		variable.default_value = "5120"
		variable.save()

		variable.set_on_server(db_1.name)
		db_1.reload()
		db_2.reload()
		self.assertEqual(db_1.mariadb_system_variables[0].value, 5120 * 1024 * 1024)
		self.assertEqual(db_2.mariadb_system_variables[0].value, 1024 * 1024 * 1024)

		variable = frappe.get_doc("MariaDB Variable", "innodb_old_blocks_time")
		variable.default_value = "5000"
		variable.save()

		variable.set_on_server(db_2.name)
		db_1.reload()
		db_2.reload()
		self.assertEqual(db_1.mariadb_system_variables[1].value, "1000")
		self.assertEqual(db_2.mariadb_system_variables[1].value, "5000")
