from contextlib import suppress

from frappe.core.doctype.log_settings.log_settings import clear_log_table


def execute():
	with suppress(Exception):
		clear_log_table("Alertmanager Webhook Log", days=60)
