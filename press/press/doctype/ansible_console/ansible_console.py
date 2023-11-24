# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json
import shutil
import frappe
from frappe.model.document import Document
from ansible import context
from ansible import constants

from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader

from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from frappe.utils import get_timedelta


class AnsibleConsole(Document):
	def run(self):
		frappe.only_for("System Manager")
		try:
			ad_hoc = AnsibleAdHoc(sources=self.inventory)
			for host in ad_hoc.run(self.command):
				self.append("output", host)
		except Exception:
			self.error = frappe.get_traceback()
			import traceback

			traceback.print_exc()


@frappe.whitelist()
def execute_command(doc):
	frappe.enqueue(
		"press.press.doctype.ansible_console.ansible_console._execute_command", doc=doc
	)
	return doc


def _execute_command(doc):
	console = frappe.get_doc(json.loads(doc))
	console.run()
	return console.as_dict()


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super(AnsibleCallback, self).__init__(*args, **kwargs)
		self.hosts = {}

	def v2_runner_on_ok(self, result, *args, **kwargs):
		self.update_task("Success", result)

	def v2_runner_on_failed(self, result, *args, **kwargs):
		self.update_task("Failure", result)

	def v2_runner_on_unreachable(self, result):
		self.update_task("Unreachable", result)

	def update_task(self, status, result):
		host, result = self.parse_result(result)
		result.update(
			{
				"host": host,
				"status": status,
			}
		)
		self.hosts[host] = result

	def parse_result(self, result):
		host = result._host.get_name()
		_result = result._result
		return host, frappe._dict(
			{
				"output": _result.get("stdout"),
				"error": _result.get("stderr"),
				"exception": _result.get("msg"),
				"exit_code": _result.get("rc"),
				"duration": get_timedelta(_result.get("delta", "0:00:00.000000")),
			}
		)


class AnsibleAdHoc:
	def __init__(self, sources):
		constants.HOST_KEY_CHECKING = False
		context.CLIARGS = ImmutableDict(
			become_method="sudo",
			check=False,
			connection="ssh",
			extra_vars=[],
			remote_user="root",
			start_at_task=None,
			syntax=False,
			verbosity=3,
		)

		self.loader = DataLoader()
		self.passwords = dict({})

		self.inventory = InventoryManager(loader=self.loader, sources=sources)
		self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

		self.callback = AnsibleCallback()

	def run(self, command):
		self.tasks = [dict(action=dict(module="shell", args=command))]
		source = dict(
			name="Ansible Play",
			hosts="all",
			gather_facts="no",
			tasks=self.tasks,
		)

		self.play = Play().load(
			source, variable_manager=self.variable_manager, loader=self.loader
		)

		tqm = TaskQueueManager(
			inventory=self.inventory,
			variable_manager=self.variable_manager,
			loader=self.loader,
			passwords=self.passwords,
			stdout_callback=self.callback,
			forks=16,
		)

		try:
			tqm.run(self.play)
		finally:
			tqm.cleanup()
			self.loader.cleanup_all_tmp_files()

		shutil.rmtree(constants.DEFAULT_LOCAL_TMP, True)

		return list(self.callback.hosts.values())
