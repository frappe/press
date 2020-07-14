from __future__ import unicode_literals

import frappe


@frappe.whitelist(allow_guest=True)
def script():
	migration_script = "../apps/press/press/scripts/migrate.py"
	return open(migration_script).read()
