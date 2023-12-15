# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from functools import cached_property
import frappe
import json
from frappe.model.document import Document
from press.telegram_utils import Telegram
from press.utils import log_error
from frappe.utils import get_url_to_form
from frappe.utils.data import add_to_date


TELEGRAM_NOTIFICATION_TEMPLATE = """
*{{ status }}* - *{{ severity }}*: {{ rule.name }} on {{ combined_alerts }} instances

{{ rule.description }}

Instances:
{%- for instance in instances %}
	- [{{ instance["name"] }}]({{ instance["link"] }}) [→]({{ instance["name"] }})
{%- endfor %}

{% if labels -%}
Labels:
{%- for key, value in labels.items() %}
	- {{ key }}: {{ value }}
{%- endfor %}
{%- endif %}

"""

INCIDENT_ALERT = "Sites Down"  # TODO: make it a field or child table somewhere #
INCIDENT_SCOPE = "server"


class AlertmanagerWebhookLog(Document):
	def validate(self):
		self.parsed = json.loads(self.payload)
		self.alert = self.parsed["groupLabels"]["alertname"]
		self.status = self.parsed["status"].capitalize()
		self.severity = self.parsed["commonLabels"]["severity"].capitalize()
		self.group_key = self.parsed["groupKey"]
		self.external_url = self.parsed["externalURL"]
		self.truncated_alerts = self.parsed["truncatedAlerts"]
		self.combined_alerts = len(self.parsed["alerts"])
		self.common_labels = json.dumps(self.parsed["commonLabels"], indent=2, sort_keys=True)
		self.common_annotations = json.dumps(
			self.parsed["commonAnnotations"], indent=2, sort_keys=True
		)
		self.group_labels = json.dumps(self.parsed["groupLabels"], indent=2, sort_keys=True)
		self.common_labels = json.dumps(self.parsed["commonLabels"], indent=2, sort_keys=True)

		self.payload = json.dumps(self.parsed, indent=2, sort_keys=True)
		frappe.enqueue_doc(
			self.doctype, self.name, "send_telegram_notification", enqueue_after_commit=True
		)

	def after_insert(self):
		self.validate_and_create_incident()

	def get_past_alert_instances(self):
		past_alerts = frappe.get_all(
			self.doctype,
			fields=["payload"],
			filters={
				"alert": self.alert,
				"severity": self.severity,
				"status": self.status,
				"group_key": ("like", f"%{self.group_labels.get(INCIDENT_SCOPE)}%"),
				"creation": [
					">",
					add_to_date(frappe.utils.now(), hours=-self.get_repeat_interval()),
				],
			},
			group_by="group_key",
		)  # get site down alerts grouped by benches

		instances = []
		for alert in past_alerts:
			payload = json.loads(alert["payload"])
			instances.extend(
				[alert["alerts"]["labels"]["instance"] for alert in payload["alerts"]]
			)
		return set(instances)

	def total_instances(self) -> int:
		return frappe.db.count(
			"Site", {"status": "Active", INCIDENT_SCOPE: self.group_labels.get(INCIDENT_SCOPE)}
		)

	def validate_and_create_incident(self):
		if not (
			self.alert == INCIDENT_ALERT
			and self.severity == "Critical"
			and self.status == "Firing"
		):
			return

		instances = self.get_past_alert_instances()
		if len(instances) > 0.8 * self.total_instances():
			self.create_incident()

	def get_repeat_interval(self):
		repeat_interval = frappe.db.get_value(
			"Prometheus Alert Rule", self.alert, "repeat_interval"
		)
		hours = repeat_interval.split("h")[0]  # assume hours
		return int(hours)

	def generate_telegram_message(self):
		context = self.as_dict()
		rule = frappe.get_doc("Prometheus Alert Rule", self.alert)

		self.parsed = json.loads(self.payload)
		self.instances = [
			{
				"name": alert["labels"]["instance"],
				"doctype": alert["labels"].get(
					"doctype", self.guess_doctype(alert["labels"]["instance"])
				),
			}
			for alert in self.parsed["alerts"][:20]
		]

		labels = self.parsed["groupLabels"]
		labels.pop("alertname", None)

		for instance in self.instances:
			if instance["doctype"]:
				instance["link"] = get_url_to_form(instance["doctype"], instance["name"])

		context.update({"instances": self.instances, "labels": labels, "rule": rule})
		message = frappe.render_template(TELEGRAM_NOTIFICATION_TEMPLATE, context)

		return message

	def guess_doctype(self, name):
		doctypes = [
			"Site",
			"Bench",
			"Server",
			"Proxy Server",
			"Database Server",
			"Monitor Server",
			"Log Server",
			"Registry Server",
			"Analytics Server",
			"Site Domain",
			"Trace Server",
		]
		for doctype in doctypes:
			if frappe.db.exists(doctype, name):
				return doctype

	def send_telegram_notification(self):
		message = self.generate_telegram_message()
		client = Telegram(self.severity)
		client.send(message)

	@property
	def bench(self):
		return self.group_labels.get("bench")

	@property
	def cluster(self):
		return self.group_labels.get("cluster")

	@property
	def server(self):
		return self.group_labels.get("server")

	@cached_property
	def group_labels(self) -> dict:
		parsed = json.loads(self.payload)
		return parsed["groupLabels"]

	def create_incident(self):
		try:
			if incident_exists := frappe.db.exists(
				"Incident",
				filters={
					"alert": self.alert,
					"bench": self.bench,
					"server": self.server,
					"cluster": self.cluster,
					"status": "Validating",
					"creation": ["<=", add_to_date(frappe.utils.now(), minutes=-10)],
				},
			):
				incident = frappe.get_doc("Incident", incident_exists)
			else:
				incident = frappe.new_doc("Incident")
				incident.alert = self.alert
				incident.bench = self.bench
				incident.server = self.server
				incident.cluster = self.cluster

			incident.append(
				"alerts",
				{
					"alert": self.name,
					"combined_alerts": self.combined_alerts,
				},
			)
			incident.save()
		except Exception as e:
			log_error("Failed to create incident", e)
