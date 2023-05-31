# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.server.server import BaseServer


@patch.object(BaseServer, "after_insert", new=Mock())
def create_test_database_server():
	"""Create test Database Server doc"""
	return frappe.get_doc(
		{
			"doctype": "Database Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"agent_password": frappe.mock("password"),
			"hostname": "m",
			"cluster": "Default",
		}
	).insert(ignore_if_duplicate=True)


class TestDatabaseServer(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_multiple_values_for_same_mariadb_system_variable_cant_be_set(self):
		"""Test that multiple values for same MariaDB system variable can't be set"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 2000},
		)

		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_only_one_datatype_value_can_be_set_for_one_mariadb_variable(self):
		"""Test that only one datatype value can be set for one MariaDB variable"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{
				"mariadb_variable": "innodb_buffer_pool_size",
				"value_int": 1000,
				"value_bool": True,
			},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_wrong_datatype_value_cannot_be_set_for_variable(self):
		"""Test that wrong datatype value cannot be set for variable"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": True},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_value_field_set_matches_datatype(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{
				"mariadb_variable": "innodb_buffer_pool_size",
				"value_bool": 1000,  # seeing if only value is checked and not the field
			},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_only_bool_variables_can_be_skipped(self):
		"""Test that only bool variables can be skipped"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000, "skip": True},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()
