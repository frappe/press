# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAnsibleConsole(FrappeTestCase):
	def test_ansible_console_run(self):
		console = frappe.get_doc("Ansible Console")
		console.inventory = "localhost,"
		console.command = "ls"
		console.run()

		self.assertEqual(len(console.output), 1)
		output = console.output[0]

		self.assertEqual(output.host, "localhost")
		self.assertEqual(output.status, "Unreachable")

	def test_ansible_console_run_creates_console_log(self):
		count_before = frappe.db.count("Ansible Console Log")

		console = frappe.get_doc("Ansible Console")
		console.inventory = "localhost,"
		console.command = "ls"
		console.run()

		count_after = frappe.db.count("Ansible Console Log")
		self.assertEqual(count_before + 1, count_after)
