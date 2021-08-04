# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.model.document import Document
from frappe.modules.utils import export_module_json

BOILERPLATE = """# Copyright (c) {year}, Frappe and contributors
# For license information, please see license.txt

# import frappe
from press.press.ui_action.base_action import BaseAction

class {action_name}(BaseAction):
	def execute(self, arg1=None, arg2=None):
		pass
"""


class UIAction(Document):
	def on_update(self):
		path = export_module_json(self, True, "Press")
		if path and not os.path.exists(path + ".py"):
			with open(path + ".py", "w") as f:
				action_name = self.name.replace(" ", "")
				f.write(BOILERPLATE.format(action_name=action_name, year=frappe.utils.today()[:4]))

	def is_authorized(self):
		roles = [d.role for d in self.roles]
		return frappe.utils.has_common(roles, frappe.get_roles())

	def get_object(self):
		scrubbed_name = frappe.scrub(self.name)
		ActionClass = frappe.get_attr(
			f"press.press.ui_action.{scrubbed_name}.{scrubbed_name}.{self.name.replace(' ', '')}"
		)
		return ActionClass()

	def execute(self, **kwargs):
		if not self.is_authorized():
			frappe.throw(f"Cannot execute action {self.name}", frappe.PermissionError)

		action = self.get_object()
		return action.execute(**kwargs)
