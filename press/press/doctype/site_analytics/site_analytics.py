# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SiteAnalytics(Document):
	pass


def create_site_analytics(site, data):
	def get_last_logins(analytics):
		last_logins = []
		for login in analytics.get("last_logins", []):
			last_logins.append(
				{
					"user": login["user"],
					"full_name": login["full_name"],
					"timestamp": login["creation"],
				}
			)
		return last_logins

	def get_sales_data(analytics):
		sales_data = []
		for row in analytics.get("activation", {}).get("sales_data", []):
			doctype, count = tuple(row.items())[0]
			if count:
				sales_data.append(
					{
						"document_type": doctype,
						"count": count,
					}
				)
		return sales_data

	timestamp = data["timestamp"]
	analytics = data["analytics"]
	if not frappe.db.exists("Site Analytics", {"site": site, "timestamp": timestamp}):
		doc = frappe.get_doc(
			{
				"doctype": "Site Analytics",
				"site": site,
				"timestamp": timestamp,
				"country": analytics.get("country"),
				"time_zone": analytics.get("time_zone"),
				"language": analytics.get("language"),
				"scheduler_enabled": analytics.get("scheduler_enabled"),
				"setup_complete": analytics.get("setup_complete"),
				"space_used": analytics.get("space_used"),
				"backup_size": analytics.get("backup_size"),
				"database_size": analytics.get("database_size"),
				"files_size": analytics.get("files_size"),
				"emails_sent": analytics.get("emails_sent"),
				"installed_apps": analytics.get("installed_apps", []),
				"users": analytics.get("users", []),
				"last_logins": get_last_logins(analytics),
				"company": analytics.get("company"),
				"domain": analytics.get("domain"),
				"activation_level": analytics.get("activation", {}).get("activation_level"),
				"sales_data": get_sales_data(analytics),
			}
		)
		doc.insert()
