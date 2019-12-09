# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.core.utils import find


class Bench(Document):
	def new_site(self, name):
		frappe_app = find(self.apps, lambda a: a.scrubbed == "frappe")
		site = frappe.get_doc(
			{
				"doctype": "Site",
				"name": f"{name}.frappe.cloud",
				"bench": self.name,
				"server": self.server,
				"password": frappe.generate_hash(length=16),
				"apps": [
					{
						"app": frappe_app.app,
						"hash": frappe_app.hash,
						"scrubbed": frappe_app.scrubbed,
						"version": frappe_app.version,
					}
				],
			}
		)
		site.insert()
		return site
