# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from io import StringIO
import time

import pexpect

import frappe
from frappe.model.document import Document
from press.press.doctype.deploy_candidate.deploy_candidate import ansi_escape


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
		frappe.db.commit()

	def _run_reboot(self):
		credentials = frappe.get_doc(
			"Virtual Machine", self.virtual_machine
		).get_serial_console_credentials()
		ssh = pexpect.spawn(credentials["command"], encoding="utf-8")
		ssh.logfile = FakeIO(self)

		index = ssh.expect([credentials["fingerprint"], pexpect.TIMEOUT], timeout=3)
		if index == 0:
			ssh.expect("Are you sure you want to continue")
			ssh.sendline("yes")

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


class FakeIO(StringIO):
	def __init__(self, serial_console_log, *args, **kwargs):
		self.console = serial_console_log.name
		super().__init__(*args, **kwargs)

	def flush(self):
		super().flush()
		output = ansi_escape(self.getvalue())
		frappe.db.set_value(
			"Serial Console Log", self.console, "output", output, update_modified=False
		)

		message = {"name": self.console, "output": output}
		frappe.publish_realtime(
			event="serial_console_log_update",
			doctype="Serial Console Log",
			docname=self.console,
			user=frappe.session.user,
			message=message,
		)

		frappe.db.commit()


@frappe.whitelist()
def run_reboot(doc):
	frappe.only_for("System Manager")
	parsed_doc = frappe.parse_json(doc)
	frappe.get_doc(parsed_doc.doctype, parsed_doc.name).run_reboot()
	return doc
