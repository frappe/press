from math import ceil

import frappe

groups = frappe.get_all(
	"Release Group",
	filters={"gunicorn_threads_per_worker": (">", 0)},
	or_filters={"min_gunicorn_workers": (">", 0), "max_gunicorn_workers": (">", 0)},
	fields=["name", "min_gunicorn_workers", "gunicorn_threads_per_worker", "max_gunicorn_workers"],
)


def execute():
	for group in groups:
		new_min = ceil(group.min_gunicorn_workers / group.gunicorn_threads_per_worker)
		frappe.db.set_value("Release Group", group.name, "min_gunicorn_workers", new_min)
		new_max = ceil(group.max_gunicorn_workers / group.gunicorn_threads_per_worker)
		frappe.db.set_value("Release Group", group.name, "max_gunicorn_workers", new_max)
		print(f"""
	Updated Release Group {group.name}:
	before: Min: {group.min_gunicorn_workers}, Max: {group.max_gunicorn_workers}
	after:  Min: {new_min}, Max: {new_max}
	""")
