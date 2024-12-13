import frappe

from press.press.doctype.devbox.devbox import Devbox


def sync_all_active_devboxes():
	devboxes = frappe.get_all("Devbox", filters={"is_removed": False}, pluck="name")
	print(devboxes)
	for devbox_name in devboxes:
		frappe.enqueue(
			"press.press.doctype.devbox.devbox_helper.sync_devbox",
			devbox_name=devbox_name,
			queue="sync",
			deduplicate=True,
			enqueue_after_commit=True,
			job_id=f"sync_devbox:{devbox_name}",
		)


def sync_devbox(devbox_name):
	devbox = Devbox("Devbox", devbox_name)
	devbox.sync_devbox_status()
	devbox.sync_devbox_docker_volumes_size()
