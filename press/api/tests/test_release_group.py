import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.api.client import get_list


class TestAPIReleaseGroupEnvironmentVariable(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_fetch_environment_variables(self):
		rg = create_test_release_group([create_test_app()])
		environment_variables = [
			{"key": "test_key", "value": "test_value", "internal": False},
			{"key": "test_key_2", "value": "test_value", "internal": False},
			{"key": "secret_key", "value": "test_value", "internal": True},
		]
		for env in environment_variables:
			rg.append("environment_variables", env)
		rg.save()
		rg.reload()

		fetched_environment_variable_list = get_list(
			"Release Group Variable",
			fields=["name", "key", "value"],
			filters={"parenttype": "Release Group", "parent": rg.name},
		)
		self.assertEqual(len(fetched_environment_variable_list), 2)
		internal_environment_variables_keys = [
			env["key"] for env in environment_variables if env["internal"]
		]
		non_internal_environment_variables_keys = [
			env["key"] for env in environment_variables if not env["internal"]
		]
		for env in fetched_environment_variable_list:
			self.assertNotIn(env.key, internal_environment_variables_keys)
			self.assertIn(env.key, non_internal_environment_variables_keys)

	def test_add_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.update_environment_variable({"test_key": "test_value"})
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		self.assertEqual(rg.environment_variables[0].key, "test_key")
		self.assertEqual(rg.environment_variables[0].value, "test_value")

	def test_update_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append(
			"environment_variables", {"key": "test_key", "value": "test_value", "internal": 0}
		)
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.update_environment_variable({"test_key": "new_test_value"})
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		self.assertEqual(rg.environment_variables[0].value, "new_test_value")

	def test_update_internal_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append(
			"environment_variables", {"key": "test_key", "value": "test_value", "internal": 1}
		)
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)

		def update_internal_environment_variable():
			rg.update_environment_variable({"test_key": "new_test_value"})

		self.assertRaises(frappe.ValidationError, update_internal_environment_variable)

	def test_delete_internal_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append(
			"environment_variables", {"key": "test_key", "value": "test_value", "internal": 1}
		)
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.delete_environment_variable("test_key")
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)

	def test_delete_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append(
			"environment_variables", {"key": "test_key", "value": "test_value", "internal": 0}
		)
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.delete_environment_variable("test_key")
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 0)
