from __future__ import unicode_literals

import frappe
from press.utils import get_minified_script


@frappe.whitelist(allow_guest=True)
def script():
	return get_minified_script()
