# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ReleaseGroup(Document):
	def create_deploy_candidate(self):
		releases = []
		for app in self.apps:
			release = frappe.get_all(
				"App Release",
				fields=["name", "app", "hash"],
				filters={"app": app.app, "status": "Approved", "deployable": True},
				order_by="creation desc",
				limit=1,
			)
			if release:
				release = release[0]
				releases.append({"release": release.name, "app": release.app, "hash": release.hash})
		frappe.get_doc(
			{"doctype": "Deploy Candidate", "group": self.name, "apps": releases}
		).insert()
