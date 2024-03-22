# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class SiteAnalytics(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.site_analytics_active.site_analytics_active import (
			SiteAnalyticsActive,
		)
		from press.press.doctype.site_analytics_app.site_analytics_app import SiteAnalyticsApp
		from press.press.doctype.site_analytics_doctype.site_analytics_doctype import (
			SiteAnalyticsDocType,
		)
		from press.press.doctype.site_analytics_login.site_analytics_login import (
			SiteAnalyticsLogin,
		)
		from press.press.doctype.site_analytics_user.site_analytics_user import (
			SiteAnalyticsUser,
		)

		activation_level: DF.Int
		backup_size: DF.Int
		company: DF.Data | None
		country: DF.Data | None
		database_size: DF.Int
		domain: DF.Data | None
		emails_sent: DF.Int
		files_size: DF.Int
		installed_apps: DF.Table[SiteAnalyticsApp]
		language: DF.Data | None
		last_active: DF.Table[SiteAnalyticsActive]
		last_logins: DF.Table[SiteAnalyticsLogin]
		sales_data: DF.Table[SiteAnalyticsDocType]
		scheduler_enabled: DF.Check
		setup_complete: DF.Check
		site: DF.Link
		space_used: DF.Int
		time_zone: DF.Data | None
		timestamp: DF.Datetime
		users: DF.Table[SiteAnalyticsUser]
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=30):
		tables = [
			"Site Analytics",
			"Site Analytics User",
			"Site Analytics Login",
			"Site Analytics App",
			"Site Analytics DocType",
			"Site Analytics Active",
		]
		for table in tables:
			table = frappe.qb.DocType(table)
			frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))
			frappe.db.commit()


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

	def get_last_active(analytics):
		last_active = []
		for user in analytics.get("users", []):
			if user and user.get("enabled") == 1:
				last_active.append(user)

		return last_active

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
				"last_active": get_last_active(analytics),
				"company": analytics.get("company"),
				"domain": analytics.get("domain"),
				"activation_level": analytics.get("activation", {}).get("activation_level"),
				"sales_data": get_sales_data(analytics),
			}
		)
		doc.insert()
