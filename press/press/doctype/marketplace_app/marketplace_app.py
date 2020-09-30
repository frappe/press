# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import requests
import frappe
from base64 import b64decode
from frappe.model.document import Document
from press.api.github import get_access_token


class MarketplaceApp(Document):
	def before_insert(self):
		self.long_description = self.fetch_readme()

	def on_update(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or doc_before_save.status != self.status:
			frappe_app = frappe.get_doc("Frappe App", self.frappe_app)
			frappe_app.public = self.status == "Published"
			frappe_app.save()

	def fetch_readme(self):
		frappe_app = frappe.get_doc("Frappe App", self.frappe_app)
		token = get_access_token(frappe_app.installation)
		headers = {
			"Authorization": f"token {token}",
		}
		owner = frappe_app.repo_owner
		repository = frappe_app.repo
		branch = frappe_app.branch

		readme_content = None
		variants = ["README.md", "readme.md", "readme", "README", "Readme"]
		for variant in variants:
			try:
				readme = requests.get(
					f"https://api.github.com/repos/{owner}/{repository}/contents/{variant}",
					headers=headers,
					params={"ref": branch},
				).json()
				readme_content = b64decode(readme["content"]).decode()
				if readme_content:
					break
			except Exception:
				print(frappe.get_traceback())
				continue

		return readme_content
