# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from press.telegram_utils import Telegram


TELEGRAM_NOTIFICATION_TEMPLATE = """
*{{ status }}* - *{{ severity }}*: {{ rule.name }} on {{ combined_alerts }} instances

{{ rule.description }}

Instances:
{%- for instance in instances %}
	- {{ instance }}
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

		self.instances = [alert["labels"]["instance"] for alert in self.parsed["alerts"]]
		self.payload = json.dumps(self.parsed, indent=2, sort_keys=True)

		self.send_telegram_notification()

	def generate_telegram_message(self):
		context = self.as_dict()
		rule = frappe.get_doc("Prometheus Alert Rule", self.alert)

		labels = self.parsed["groupLabels"]
		labels.pop("alertname", None)

		context.update({"instances": self.instances[:100], "labels": labels, "rule": rule})
		message = frappe.render_template(TELEGRAM_NOTIFICATION_TEMPLATE, context)

		return message

	def send_telegram_notification(self):
		message = self.generate_telegram_message()
		Telegram().send(message)
