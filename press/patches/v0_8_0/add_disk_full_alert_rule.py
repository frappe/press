import frappe

from press.press.doctype.dashboard_banner.dashboard_banner import DISK_FULL_ALERT
from press.press.doctype.server.server import BENCH_DATA_MNT_POINT, MARIADB_DATA_MNT_POINT

MOUNTPOINTS = f"/|{BENCH_DATA_MNT_POINT}|{MARIADB_DATA_MNT_POINT}"
EXPRESSION = (
	f'node_filesystem_avail_bytes{{job="node", mountpoint=~"{MOUNTPOINTS}"}}'
	f' / node_filesystem_size_bytes{{job="node", mountpoint=~"{MOUNTPOINTS}"}} < 0.02'
)


def execute():
	if frappe.db.exists("Prometheus Alert Rule", DISK_FULL_ALERT):
		return

	if not frappe.db.get_single_value("Press Settings", "monitor_server"):
		# saving the rule pushes it to the monitor server. Nothing to push to.
		return

	frappe.get_doc(
		{
			"doctype": "Prometheus Alert Rule",
			"name": DISK_FULL_ALERT,
			"enabled": True,
			"severity": "Critical",
			"description": "Disk is almost full on {{ $labels.instance }} ({{ $labels.mountpoint }})",
			"expression": EXPRESSION,
			"for": "5m",
			# per instance, so one server recovering resolves only its own banner
			"group_by": '["alertname", "instance"]',
		}
	).insert()
