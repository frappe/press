# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AddOnSettings(Document):
	@frappe.whitelist()
	def init_etcd_data(self, proxy_server):
		# TODO: Add a separate agent job for this, instead of doing it recursively here do it on server
		subs = frappe.get_all(
			"Storage Integration Subscription",
			fields=["name", "enabled"],
			filters={"minio_server_on": proxy_server},
		)

		for sub in subs:
			doc = frappe.get_doc("Storage Integration Subscription", sub["name"])
			doc.create_user()
			if doc.enabled == 0:
				doc.update_user("disable")

			frappe.db.commit()
