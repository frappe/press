# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.core.utils import find
from frappe.model.document import Document


class Site(Document):
	def before_insert(self):
		self.bench = frappe.get_all("Bench")[0].name
		self.server = frappe.db.get_value("Bench", self.bench, "server")
		apps = frappe.get_all(
			"Installed App",
			fields=["scrubbed", "app", "hash", "version"],
			filters={"parenttype": "Bench", "parent": self.bench},
		)
		frappe_app = find(apps, lambda x: x.scrubbed == "frappe")
		self.append(
			"apps",
			{
				"app": frappe_app.app,
				"hash": frappe_app.hash,
				"scrubbed": frappe_app.scrubbed,
				"version": frappe_app.version,
			},
		)
		self.password = frappe.generate_hash(length=16)
