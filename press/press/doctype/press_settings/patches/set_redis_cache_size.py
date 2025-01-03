import frappe
from frappe.core.utils import find


def execute():
	frappe.reload_doctype("Press Settings")
	settings = frappe.get_single("Press Settings")
	if not settings.redis_cache_size:
		redis_cache_size_field = find(settings.meta.fields, lambda x: x.fieldname == "redis_cache_size")
		settings.redis_cache_size = redis_cache_size_field.default
		settings.save()
