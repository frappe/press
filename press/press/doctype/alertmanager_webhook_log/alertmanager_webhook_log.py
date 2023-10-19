# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

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
		if self.status is "Firing" and self.severity is "Critical":
			self.create_incident()
		frappe.enqueue_doc(
			self.doctype, self.name, "send_telegram_notification", enqueue_after_commit=True
		)

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

	def create_incident(self):
		# incident = frappe.new_doc("Incident")
		# incident.alert = self.alert
		parsed = json.loads(self.payload)
		try:
			bench = parsed["groupLabels"].get("bench")
			cluster = parsed["groupLabels"].get("cluster")
			server = parsed["groupLabels"].get("server")
		except Exception as e:
			log_error("Failed to create incident", e)
			return
		if incident_exists := frappe.db.exists(
			"Incident",
			filters={
				"alert": self.alert,
				"bench": bench,
				"server": server,
				"cluster": cluster,
				"status": "Validating",
				"creation": ["<=", add_to_date(frappe.utils.now(), minutes=-10)],
			},
		):
			incident = frappe.get_doc("Incident", incident_exists)
		else:
			incident = frappe.new_doc("Incident")
			incident.alert = self.alert
			incident.bench = bench
			incident.server = server
			incident.cluster = cluster

		incident.append(
			"alerts",
			{
				"alert": self.name,
				"combined_alerts": self.combined_alerts,
			},
		)
		incident.save()
