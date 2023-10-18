# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressNotification(Document):
	def after_insert(self):
		if self.type == "Bench Deploy":
			group_name = frappe.db.get_value("Deploy Candidate", self.id, "group")
			rg_title = frappe.db.get_value("Release Group", group_name, "title")

			frappe.sendmail(
				recipients=[frappe.db.get_value("Team", self.team, "user")],
				subject=f"Bench Deploy Failed - {rg_title}",
				template="bench_deploy_failure",
				args={
					"message": self.message,
					"link": f"dashboard/{self.route}",
				},
			)


def create_new_notification(team, id, type, message, route):
	if not frappe.db.exists("Press Notification", {"id": id}):
		new_notification = frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": team,
				"id": id,
				"type": type,
				"message": message,
				"route": route,
			}
		).insert()
		frappe.publish_realtime("press_notification", {"team": team})
