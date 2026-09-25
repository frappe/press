import frappe

from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	DATABASE_HIGH_CPU_ALERT,
	DATABASE_HIGH_IO_ALERT,
)


def cpu_mode_percent(mode: str) -> str:
	# mysql_up limits the node metric to database servers. Both jobs share the instance label.
	return (
		f'avg by (instance) (rate(node_cpu_seconds_total{{job="node", mode="{mode}"}}[5m])) * 100 > 50'
		f' and on (instance) mysql_up{{job="mariadb"}}'
	)


RULES = {
	DATABASE_HIGH_IO_ALERT: (
		cpu_mode_percent("iowait"),
		"Database server {{ $labels.instance }} waits on disk I/O for more than half of its time",
	),
	DATABASE_HIGH_CPU_ALERT: (
		cpu_mode_percent("user"),
		"Database server {{ $labels.instance }} has user CPU load of more than 50%",
	),
}


def execute():
	if not frappe.db.get_single_value("Press Settings", "monitor_server"):
		# saving the rule pushes it to the monitor server. Nothing to push to.
		print(f"No monitor server set. Skipping {list(RULES)}. Create them by hand once one is set up.")
		return

	for name, (expression, description) in RULES.items():
		if frappe.db.exists("Prometheus Alert Rule", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Prometheus Alert Rule",
				"name": name,
				"enabled": True,
				"severity": "Warning",
				"description": description,
				"expression": expression,
				# the banner is for sustained load, not a spike
				"for": "30m",
				# per instance, so one server recovering resolves only its own banner
				"group_by": '["alertname", "instance"]',
			}
		).insert()
