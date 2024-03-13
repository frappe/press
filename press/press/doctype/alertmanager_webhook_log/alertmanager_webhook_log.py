# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from functools import cached_property
import frappe
import json
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue_doc
from press.press.doctype.incident.incident import INCIDENT_ALERT, INCIDENT_SCOPE
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

	@property
	def incident_scope(self):
		return self.parsed_group_labels.get(INCIDENT_SCOPE)

	def after_insert(self):
		enqueue_doc(
			self.doctype, self.name, "send_telegram_notification", enqueue_after_commit=True
		)
		if self.alert == INCIDENT_ALERT:
			enqueue_doc(
				self.doctype,
				self.name,
				"validate_and_create_incident",
				enqueue_after_commit=True,
				job_id=f"validate_and_create_incident:{self.incident_scope}:{self.alert}",
				deduplicate=True,
			)

	def get_past_alert_instances(self):
		past_alerts = frappe.get_all(
			self.doctype,
			fields=["payload"],
			filters={
				"alert": self.alert,
				"severity": self.severity,
				"status": self.status,
				"group_key": ("like", f"%{self.incident_scope}%"),
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
				[alert["labels"]["instance"] for alert in payload["alerts"]]
			)  # sites
		return set(instances)

	def total_instances(self) -> int:
		return frappe.db.count(
			"Site",
			{"status": "Active", INCIDENT_SCOPE: self.incident_scope},
		)

	def validate_and_create_incident(self):
		if not frappe.db.get_single_value("Incident Settings", "enable_incident_detection"):
			return
		if not (
			self.alert == INCIDENT_ALERT
			and self.severity == "Critical"
			and self.status == "Firing"
		):
			return

		instances = self.get_past_alert_instances()
		if len(instances) > min(0.4 * self.total_instances(), 15):
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
		return self.parsed_group_labels.get("bench")

	@property
	def cluster(self):
		return self.parsed_group_labels.get("cluster")

	@property
	def server(self):
		return self.parsed_group_labels.get("server")

	@cached_property
	def parsed_group_labels(self) -> dict:
		parsed = json.loads(self.group_labels)
		return parsed

	def ongoing_incident_exists(self) -> bool:
		ongoing_incident_status = frappe.db.get_value(  # using get_value for for_update
			"Incident",
			{
				"alert": self.alert,
				INCIDENT_SCOPE: self.incident_scope,
				"status": ("in", ["Validating", "Confirmed", "Acknowledged"]),
			},
			"status",
			for_update=True,
		)
		return bool(ongoing_incident_status)

	def create_incident(self):
		try:
			if self.ongoing_incident_exists():
				return
			incident = frappe.new_doc("Incident")
			incident.alert = self.alert
			incident.server = self.server
			incident.cluster = self.cluster
			incident.save()
		except Exception:
			log_error("Incident creation failed")
