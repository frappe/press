# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import time

import pexpect

import frappe
from frappe.model.document import Document


class SerialConsoleLog(Document):
	@frappe.whitelist()
	def run_reboot(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method="_run_reboot",
			queue="long",
			enqueue_after_commit=True,
		)

	def _run_reboot(self):
		command = frappe.get_doc(
			"Virtual Machine", self.virtual_machine
		).get_serial_console_credentials()["command"]

		ssh = pexpect.spawn(command, encoding="utf-8")

		# Send a newline and wait for login prompt
		# We don't want to send break too soon
		time.sleep(0.5)
		ssh.sendline("")
		ssh.expect(["login:", "Password:"])

		# Send ~B and expect SysRq help message
		time.sleep(0.5)
		ssh.send("~B")
		time.sleep(0.1)
		ssh.send("h")
		ssh.expect(["sysrq: HELP", pexpect.TIMEOUT], timeout=1)

		break_attempt = 0
		while True:
			break_attempt += 1

			# Send ~B and then b for reboot
			time.sleep(0.5)
			ssh.sendline("")
			ssh.send("~B")
			time.sleep(0.1)
			ssh.send("b")

			# Wait for reboot
			index = ssh.expect(["sysrq: Resetting", pexpect.TIMEOUT], timeout=1)
			if index == 0 or break_attempt > 10:
				break

		# Wait for login prompt
		ssh.expect("login:", timeout=300)


@frappe.whitelist()
def run_reboot(doc):
	frappe.only_for("System Manager")
	parsed_doc = frappe.parse_json(doc)
	frappe.get_doc(parsed_doc.doctype, parsed_doc.name).run_reboot()
	return doc
