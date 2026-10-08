# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Keep bench environment variables safe to render into a Dockerfile.

Each variable becomes an `ENV KEY VALUE` line. A newline in the key or the
value ends that line, and the text after it runs as a new Dockerfile directive.
"""

import re

import frappe
from frappe import _
from frappe.utils import escape_html

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def validate_environment_variable(key: str, value: str) -> None:
	if CONTROL_CHARACTERS.search(key or "") or CONTROL_CHARACTERS.search(value or ""):
		frappe.throw(
			_("Environment variable {0} must not contain newlines or other control characters").format(
				frappe.bold(escape_html(key))
			)
		)
