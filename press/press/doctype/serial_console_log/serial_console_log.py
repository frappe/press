# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from io import StringIO

import frappe
import pexpect
from frappe.model.document import Document

from press.press.doctype.deploy_candidate.deploy_candidate import ansi_escape


class SerialConsoleLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal[
			"help",
			"reboot",
			"crash",
			"sync",
			"show-all-timers",
			"unmount",
			"show-all-locks",
			"show-backtrace-all-active-cpus",
			"show-registers",
			"show-task-states",
			"show-blocked-tasks",
			"dump-ftrace-buffer",
			"show-memory-usage",
			"terminate-all-tasks",
			"memory-full-oom-kill",
			"thaw-filesystems",
			"kill-all-tasks",
			"nice-all-RT-tasks",
			"replay-kernel-logs",
		]
		command: DF.Data | None
		message: DF.Data | None
		output: DF.Code | None
		server: DF.DynamicLink
		server_type: DF.Link
		virtual_machine: DF.Link
	# end: auto-generated types

	def validate(self):
		self.command, self.message = SYSRQ_COMMANDS.get(self.action, ("h", "HELP"))

	@frappe.whitelist()
	def run_sysrq(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method="_run_sysrq",
			queue="long",
			enqueue_after_commit=True,
			at_front=True,
		)
		frappe.db.commit()

	def _run_sysrq(self):
		credentials = frappe.get_doc("Virtual Machine", self.virtual_machine).get_serial_console_credentials()
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
			ssh.send(self.command)

			# Wait for reboot
			index = ssh.expect([f"sysrq: {self.message}", pexpect.TIMEOUT], timeout=1)
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
		frappe.db.set_value("Serial Console Log", self.console, "output", output, update_modified=False)

		message = {"name": self.console, "output": output}
		frappe.publish_realtime(
			event="serial_console_log_update",
			doctype="Serial Console Log",
			docname=self.console,
			user=frappe.session.user,
			message=message,
		)

		frappe.db.commit()


SYSRQ_COMMANDS = {
	"crash": ("c", "Trigger a crash"),
	"reboot": ("b", "Resetting"),
	"sync": ("s", "Emergency Sync"),
	"help": ("h", "HELP"),
	"show-all-timers": ("q", "Show clockevent devices & pending hrtimers (no others)"),
	"unmount": ("u", "Emergency Remount R/O"),
	"show-all-locks": ("d", "Show Locks Held"),
	"show-backtrace-all-active-cpus": ("l", "Show backtrace of all active CPUs"),
	"show-registers": ("p", "Show Regs"),
	"show-task-states": ("t", "Show State"),
	"show-blocked-tasks": ("w", "Show Blocked State"),
	"dump-ftrace-buffer": ("z", "Dump ftrace buffer"),
	"show-memory-usage": ("m", "Show Memory"),
	"terminate-all-tasks": ("e", "Terminate All Tasks"),
	"memory-full-oom-kill": ("f", "Manual OOM execution"),
	"thaw-filesystems": ("j", "Emergency Thaw of all frozen filesystems"),
	"kill-all-tasks": ("i", "Kill All Tasks"),
	"nice-all-RT-tasks": ("n", "Nice All RT Tasks"),
	"replay-kernel-logs": ("R", "Replay kernel logs on consoles"),
}


@frappe.whitelist()
def run_sysrq(doc):
	frappe.only_for("System Manager")
	parsed_doc = frappe.parse_json(doc)
	frappe.get_doc(parsed_doc.doctype, parsed_doc.name).run_sysrq()
	return doc
