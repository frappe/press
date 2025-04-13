# Copyright (c) 2023, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.runner import Ansible
from press.utils.test import foreground_enqueue_doc


@patch.object(Ansible, "run", new=Mock())
class TestDatabaseServerMariaDBVariable(FrappeTestCase):
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
				"value_str": str(1000 * 1024),
			},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_wrong_datatype_value_cannot_be_set_for_variable(self):
		"""Test that wrong datatype value cannot be set for variable"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": "OFF"},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_value_field_set_matches_datatype(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{
				"mariadb_variable": "innodb_buffer_pool_size",
				"value_str": "1000",  # seeing if only value is checked and not the field
			},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()
		server.append(
			"mariadb_system_variables",
			{
				"mariadb_variable": "log_bin",
				"value_int": False,  # seeing if only value is checked and not the field
			},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()

	def test_only_skippable_variables_can_be_skipped(self):
		"""Test that only skippable variables can be skipped"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000, "skip": True},
		)
		with self.assertRaises(frappe.ValidationError):
			server.save()
		server.reload()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "log_bin", "skip": True},
		)
		try:
			server.save()
		except frappe.ValidationError:
			self.fail("Should be able to skip skippable variables")

	@patch(
		"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_skip_implies_persist_and_not_dynamic(self, Mock_Ansible):
		"""Test that skip enables persist and not dynamic"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "log_bin", "skip": True},
		)
		server.save()
		Mock_Ansible.assert_called_once()
		args, kwargs = Mock_Ansible.call_args
		expected = {
			"server": server.name,
			"variable": "skip-log_bin",
			"dynamic": 0,
			"persist": 1,
			"skip": 1,
		}
		self.assertDictEqual(kwargs["variables"], expected)

	def test_default_value_is_applied_if_empty(self):
		"""Test that default value is applied if empty"""
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "log_bin"},
		)
		server.save()
		default_value = frappe.db.get_value("MariaDB Variable", "log_bin", "default_value")
		self.assertEqual(server.mariadb_system_variables[0].value_str, default_value)

	@patch(
		"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		wraps=foreground_enqueue_doc,
	)
	def test_ansible_playbook_triggered_with_correct_input_on_update_of_child_table(
		self, mock_enqueue_doc: Mock, Mock_Ansible
	):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		args, kwargs = Mock_Ansible.call_args
		expected_vars = {
			"server": server.name,
			"variable": "innodb_buffer_pool_size",
			"value": 1000 * 1024 * 1024,  # convert to bytes
			"dynamic": 1,
			"persist": 0,
			"skip": 0,
		}
		self.assertEqual("mysqld_variable.yml", kwargs["playbook"])
		server.reload()  # reload to get the right typing for datetime field
		self.assertDocumentEqual(server, kwargs["server"])
		self.assertDictEqual(expected_vars, kwargs["variables"])

	def test_ansible_playbook_not_triggered_on_update_of_unrelated_things(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		server.status = "Broken"
		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.save()
		Mock_Ansible.assert_not_called()

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_playbook_run_on_update_of_child_table(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		server.mariadb_system_variables[0].value_int = 2000
		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.save()
		Mock_Ansible.assert_called_once()

	@patch(
		"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		wraps=foreground_enqueue_doc,
	)
	def test_multiple_playbooks_triggered_for_multiple_variables(self, mock_enqueue_doc, Mock_Ansible):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "log_bin", "skip": True},
		)
		server.save()
		self.assertEqual(2, Mock_Ansible.call_count)

	@patch(
		"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_persist_check_passes_option_to_playbook_run(self, Mock_Ansible):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{
				"mariadb_variable": "innodb_buffer_pool_size",
				"value_int": 1000,
				"persist": True,
			},
		)
		server.save()
		args, kwargs = Mock_Ansible.call_args
		self.assertTrue(kwargs["variables"]["persist"])

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_playbook_run_on_addition_of_variable_and_only_that_variable(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.append(
				"mariadb_system_variables",
				{"mariadb_variable": "log_bin", "skip": True},
			)
			server.save()
		Mock_Ansible.assert_called_once()

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_playbook_run_only_for_variable_changed(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "log_bin", "skip": True},
		)
		server.save()
		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.mariadb_system_variables[0].value_int = 2000
			server.save()
		Mock_Ansible.assert_called_once()

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_playbooks_triggered_for_added_and_changed_variables_in_one_save(self):
		server = create_test_database_server()
		server.append(
			"mariadb_system_variables",
			{"mariadb_variable": "innodb_buffer_pool_size", "value_int": 1000},
		)
		server.save()
		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.append(
				"mariadb_system_variables",
				{"mariadb_variable": "log_bin", "skip": False},
			)
			server.mariadb_system_variables[0].value_int = 2000
			server.save()
		self.assertEqual(2, Mock_Ansible.call_count)
		for call in Mock_Ansible.call_args_list:
			args, kwargs = call
			self.assertIn(kwargs["variables"]["variable"], ["innodb_buffer_pool_size", "log_bin"])

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		wraps=foreground_enqueue_doc,
	)
	def test_background_jobs_not_created_for_new_server_doc(self, mock_enqueue_doc):
		create_test_database_server()
		mock_enqueue_doc.assert_not_called()

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		wraps=foreground_enqueue_doc,
	)
	def test_update_of_doc_with_member_that_is_not_a_field_works(self, mock_enqueue_doc):
		server = create_test_database_server()
		server.reload()
		server.x = 4096  # member that is not field
		try:
			server.save()
		except Exception:
			self.fail("Update of doc without variables failed")

	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_add_variable_method_adds_and_updates_variables(self):
		server = create_test_database_server()

		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.add_or_update_mariadb_variable("tmp_disk_table_size", "value_int", value=10241)
			Mock_Ansible.assert_called_once()

		server.reload()
		self.assertEqual(1, len(server.mariadb_system_variables))
		self.assertEqual("tmp_disk_table_size", server.mariadb_system_variables[0].mariadb_variable)
		self.assertEqual(10241, server.mariadb_system_variables[0].value_int)

		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.add_or_update_mariadb_variable("tmp_disk_table_size", "value_int", value=10242)
			Mock_Ansible.assert_called_once()

		self.assertEqual(1, len(server.mariadb_system_variables))
		self.assertEqual("tmp_disk_table_size", server.mariadb_system_variables[0].mariadb_variable)
		self.assertEqual(10242, server.mariadb_system_variables[0].value_int)

		with patch(
			"press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable.Ansible",
			wraps=Ansible,
		) as Mock_Ansible:
			server.add_or_update_mariadb_variable("tmp_disk_table_size", "value_int", 10242)  # no change
			Mock_Ansible.assert_not_called()
