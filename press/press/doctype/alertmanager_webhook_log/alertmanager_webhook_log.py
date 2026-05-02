# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import math
from functools import cached_property
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import get_url_to_form
from frappe.utils.background_jobs import enqueue_doc
from frappe.utils.data import add_to_date
from frappe.utils.synchronization import filelock

from press.exceptions import AlertRuleNotEnabled
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.incident.incident import Incident
	from press.press.doctype.incident_settings.incident_settings import IncidentSettings
	from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import (
		PrometheusAlertRule,
	)

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
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.alertmanager_webhook_log_reaction_job.alertmanager_webhook_log_reaction_job import (
			AlertmanagerWebhookLogReactionJob,
		)

		alert: DF.Link
		combined_alerts: DF.Int
		common_labels: DF.Code
		external_url: DF.Data
		group_key: DF.Code
		group_labels: DF.Code
		payload: DF.Code
		reaction_jobs: DF.Table[AlertmanagerWebhookLogReactionJob]
		severity: DF.Literal["Critical", "Warning", "Information"]
		status: DF.Literal["Firing", "Resolved"]
		truncated_alerts: DF.Int
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=10):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Alertmanager Webhook Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

	def validate(self):
		self.parsed = json.loads(self.payload)
		self.alert = self.parsed["groupLabels"].get("alertname")
		if not self.alert:
			raise AlertRuleNotEnabled("No alertname found in groupLabels")
		self.status = self.parsed["status"].capitalize()
		self.severity = self.parsed["commonLabels"]["severity"].capitalize()
		self.group_key = self.parsed["groupKey"]
		self.external_url = self.parsed["externalURL"]
		self.truncated_alerts = self.parsed["truncatedAlerts"]
		self.combined_alerts = len(self.parsed["alerts"])
		self.common_labels = json.dumps(self.parsed["commonLabels"], indent=2, sort_keys=True)
		self.group_labels = json.dumps(self.parsed["groupLabels"], indent=2, sort_keys=True)

		self.payload = json.dumps(self.parsed, indent=2, sort_keys=True)

	@property
	def bench(self) -> str | None:
		return self.parsed_group_labels.get("bench")

	@property
	def cluster(self) -> str | None:
		return self.parsed_group_labels.get("cluster")

	@property
	def server(self) -> str | None:
		return self.parsed_group_labels.get("server")

	@cached_property
	def parsed_group_labels(self) -> dict[str, str]:
		return json.loads(self.group_labels)

	@cached_property
	def alert_rule(self) -> "PrometheusAlertRule":
		return frappe.get_doc("Prometheus Alert Rule", self.alert)

	def after_insert(self):
		self.create_incident_if_necessary()
		self.check_incident_resolution_if_necessary()
		self.trigger_reaction()
		self.send_notifications()

	def create_incident_if_necessary(self):
		if not (
			self.alert == "Sites Down"
			and self.parsed_group_labels.get("server")
			and self.severity == "Critical"
			and self.status == "Firing"
		):
			return

		if not frappe.db.get_single_value("Incident Settings", "enable_incident_detection"):
			return

		if find(self.alert_rule.ignore_on_clusters, lambda x: x.cluster == self.cluster):
			return

		firing_instances = len(self.past_alert_instances("Firing"))
		total_instances = frappe.db.count(
			"Site",
			{
				"status": "Active",
				"server": self.parsed_group_labels.get("server"),
				"is_monitoring_disabled": 0,
			},
		)
		settings: IncidentSettings = frappe.get_cached_doc("Incident Settings")
		if not firing_instances > min(
			math.floor((float(settings.minimum_firing_instances_in_percent) / 100) * total_instances),
			settings.minimum_firing_instances,
		):
			return

		frappe.enqueue_doc(self.doctype, self.name, "create_incident", enqueue_after_commit=True)

	def create_incident(self):
		try:
			with filelock(f"incident_creation_{self.server}"):
				is_ongoing_incident_exist = bool(
					frappe.db.get_value(
						"Incident",
						{
							"server": self.parsed_group_labels.get("server"),
							"status": ("in", ["Validating", "Confirmed", "Acknowledged"]),
						},
						"status",
						for_update=True,  # To get latest incidents already committed; required because 2 jobs can start at the same time
					)
				)
				if is_ongoing_incident_exist:
					frappe.db.commit()  # commit the lock to avoid any lock
					return

				incident: Incident = frappe.new_doc("Incident")
				incident.server = self.server
				incident.cluster = self.cluster
				incident.save()
				frappe.db.commit()  # commit inside filelock to avoid deadlock when inserting in gap
		except Exception:
			log_error("Incident creation failed")

	def check_incident_resolution_if_necessary(self):
		"""On a Resolved webhook, find the ongoing incident for this scope and ask it to
		re-evaluate against live Prometheus state."""
		if not (self.alert == "Sites Down" and self.status == "Resolved"):
			return

		incident_name = frappe.db.get_value(
			"Incident",
			{
				"alert": self.alert,
				"server": self.parsed_group_labels.get("server"),
				"status": ("in", ["Validating", "Confirmed", "Acknowledged"]),
			},
			"name",
		)
		if not incident_name:
			return

		frappe.enqueue_doc(
			"Incident",
			incident_name,
			"check_resolved",
			enqueue_after_commit=True,
			job_id=f"incident||check_resolved||{incident_name}",
			deduplicate=True,
		)

	def trigger_reaction(self):
		if self.status != "Firing":
			return

		if not self.alert_rule.press_job_type:
			return

		enqueue_doc(
			self.doctype,
			self.name,
			"react_to_alert",
			enqueue_after_commit=True,
			job_id=f"react:{self.alert}:{self.server}",
			deduplicate=True,
		)

	def send_notifications(self):
		if frappe.get_cached_value("Prometheus Alert Rule", self.alert, "silent"):
			return

		if frappe.db.get_single_value("Press Settings", "send_telegram_notifications"):
			enqueue_doc(self.doctype, self.name, "send_telegram_notification", enqueue_after_commit=True)

		if frappe.db.get_single_value("Press Settings", "send_email_notifications"):
			enqueue_doc(self.doctype, self.name, "send_email_notification", enqueue_after_commit=True)

	def react_to_alert(self):
		for instance in self.get_instances_from_alerts_payload(self.payload):
			instance_type = self._guess_doctype(instance)
			if not instance_type:
				continue  # Prometheus is monitoring instances we don't know about

			reaction_job = self.alert_rule.react(
				instance_type, instance, self.get_labels_for_instance(instance)
			)
			if not reaction_job:
				continue

			self.append(
				"reaction_jobs",
				{
					"press_job_type": reaction_job.job_type,
					"press_job": reaction_job.name,
				},
			)

		self.save()

	# Helper methods
	def get_instances_from_alerts_payload(self, payload: str) -> set[str]:
		instances: list[str] = []
		payload = json.loads(payload)
		# List of sites
		instances.extend([alert["labels"]["instance"] for alert in payload["alerts"]])  # type: ignore
		return set(instances)

	def get_labels_for_instance(self, instance: str) -> dict:
		# Find first alert that matches the instance
		payload = json.loads(self.payload)
		alert = find(payload["alerts"], lambda x: x["labels"]["instance"] == instance)
		if alert:
			return alert["labels"]
		return {}

	def past_alert_instances(self, status: Literal["Firing", "Resolved"]) -> set[str]:
		past_alerts = frappe.get_all(
			self.doctype,
			fields=["payload"],
			filters={
				"alert": self.alert,
				"severity": self.severity,
				"status": status,
				"group_key": ("like", f"%{self.incident_scope}%"),
				"modified": [
					">",
					add_to_date(frappe.utils.now(), hours=-self.get_repeat_interval()),
				],
			},
			group_by="group_key",
			ignore_ifnull=True,
		)  # get site down alerts grouped by benches

		instances: list[str] = []
		for alert in past_alerts:
			instances.extend(self.get_instances_from_alerts_payload(alert["payload"]))

		return set(instances)

	def get_repeat_interval(self):
		repeat_interval = str(frappe.db.get_value("Prometheus Alert Rule", self.alert, "repeat_interval"))
		assert repeat_interval.endswith("h"), f"Repeat interval not in hours: {repeat_interval}"
		hours = repeat_interval.split("h")[0]  # only handles hours
		return int(hours)

	def send_telegram_notification(self):
		message = self._generate_telegram_message()
		TelegramMessage.enqueue(message=message, topic=self.severity)

	def send_email_notification(self):
		recipient_emails = frappe.db.get_single_value("Press Settings", "email_recipients") or ""
		email_list = [email.strip() for email in recipient_emails.split(",") if email.strip()]
		if not email_list:
			return

		message = self._generate_telegram_message()
		frappe.sendmail(
			recipients=email_list,
			subject=self.alert,
			message=message,
		)

	def _generate_telegram_message(self):
		context = self.as_dict()
		rule = frappe.get_doc("Prometheus Alert Rule", self.alert)

		self.parsed = json.loads(self.payload)
		self.instances = [
			{
				"name": alert["labels"]["instance"],
				"doctype": alert["labels"].get("doctype", self._guess_doctype(alert["labels"]["instance"])),
			}
			for alert in self.parsed["alerts"][:20]
		]

		labels = self.parsed["groupLabels"]
		labels.pop("alertname", None)

		for instance in self.instances:
			if instance["doctype"]:
				instance["link"] = get_url_to_form(instance["doctype"], instance["name"])

		context.update({"instances": self.instances, "labels": labels, "rule": rule})
		return frappe.render_template(TELEGRAM_NOTIFICATION_TEMPLATE, context)

	def _guess_doctype(self, name: str) -> Document | None:
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
			"NFS Server",
		]
		for doctype in doctypes:
			if frappe.db.exists(doctype, name):
				return doctype
		return None
