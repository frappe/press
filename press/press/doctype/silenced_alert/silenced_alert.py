# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import timezone
from frappe.utils.data import format_duration, get_datetime
from press.utils import log_error
import requests
import base64
import json


class SilencedAlert(Document):
	def validate(self):
		self.get_duration()

	def get_duration(self):
		diff = get_datetime(self.to_time) - get_datetime(self.from_time)
		self.duration = format_duration(diff.total_seconds())

	def get_keyword_based_on_instance_type(self):
		match self.instance_type:
			case "Site":
				return "instance"
			case "Server":
				return "instance"
			case "Cluster":
				return "cluster"
			case "Release Group":
				return "group"
			case "Bench":
				return "bench"
			case "Prometheus Alert Rule":
				return "alertname"
			case _:
				return ""

	@frappe.whitelist()
	def preview_alerts(self):
		monitor_server = frappe.get_doc(
			"Monitor Server", "monitor.athul.fc.frappe.dev"
		)  # frappe.db.get_single_value("Press Settings","monitor_server"))
		auth_token = base64.b64encode(
			f"frappe:{monitor_server.get_password('grafana_password')}".encode("utf-8")
		).decode("utf-8")
		# keyword = f'{self.get_keyword_based_on_instance_type()}%3D%22{self.instance.replace(" ","%20")}%22'
		keyword = f'{self.get_keyword_based_on_instance_type()}="{"erpdb.innoterra.co.in" or self.instance}"'
		print(keyword)
		res = requests.get(
			f"https://monitor.frappe.cloud/alertmanager/api/v2/alerts/groups?filter={keyword}&silenced=false&active=true",
			headers={"Authorization": f"Basic {auth_token}"},
		)
		if res.status_code == 200:
			alerts = res.json()
			self.total_alerts = len(alerts)
			self.alert_previews = json.dumps(alerts, indent=2)
			self.save()
		else:
			frappe.throw("Unable to fetch alerts from Alertmanager")

	@frappe.whitelist()
	def create_new_silence(self):
		monitor_server = frappe.get_doc(
			"Monitor Server", "monitor.athul.fc.frappe.dev"
		)  # frappe.db.get_single_value("Press Settings","monitor_server"))
		auth_token = base64.b64encode(
			f"frappe:{monitor_server.get_password('grafana_password')}".encode("utf-8")
		).decode("utf-8")
		data = {
			"matchers": [
				{
					"name": self.get_keyword_based_on_instance_type(),
					"value": "erpdb.innoterra.co.in",
					"isRegex": False,
					"isEqual": True,
				}
			],
			"startsAt": get_datetime(self.from_time).astimezone(timezone.utc).isoformat(),
			"endsAt": get_datetime(self.to_time).astimezone(timezone.utc).isoformat(),
			"createdBy": self.owner,
			"comment": self.alert_comment,
			"id": None,
		}
		res = requests.post(
			"https://monitor.frappe.cloud/alertmanager/api/v2/silences",
			headers={"Authorization": f"Basic {auth_token}"},
			json=data,
		)
		if res.status_code == 200:
			alerts = res.json()
			self.status = "Active"
			self.silence_id = alerts["silenceID"]
			self.save()
		else:
			frappe.throw("Unable to fetch alerts from Alertmanager")


def check_silenced_alerts():
	"""
	Checks for silenced alerts in Alertmanager and updates the status of the silenced alert in Press
	Runs every hour
	"""
	silences = frappe.get_all(
		"Silenced Alert", fields=["silence_id"], filters={"status": "Active"}
	)
	monitor_server = frappe.get_doc(
		"Monitor Server", "monitor.athul.fc.frappe.dev"
	)  # frappe.db.get_single_value("Press Settings","monitor_server"))
	auth_token = base64.b64encode(
		f"frappe:{monitor_server.get_password('grafana_password')}".encode("utf-8")
	).decode("utf-8")
	req = requests.get(
		"https://monitor.frappe.cloud/alertmanager/api/v2/silences?silenced=false&inhibited=false&active=true",
		headers={"Authorization": f"Basic {auth_token}"},
	)
	if req.status_code == 200:
		silences_from_alertmanager = req.json()
		s_ids = [x["silence_id"] for x in silences]
		for silence in silences_from_alertmanager:
			if not silence["status"]["state"] == "active" and silence["id"] in s_ids:
				frappe.db.set_value(
					"Silenced Alert", {"silence_id": silence["id"]}, "status", "Expired"
				)
		frappe.db.commit()
	else:
		log_error("Failed to fetch silences from Alertmanager")
