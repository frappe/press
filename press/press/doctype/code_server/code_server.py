# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.utils import log_error


class CodeServer(Document):
	def autoname(self):
		self.name = self.subdomain + "." + self.domain

	def validate(self):
		if not self.proxy_server and self.has_value_changed("server"):
			self.proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")

	def after_insert(self):
		self.setup()

	def setup(self):
		try:
			agent = Agent(self.proxy_server, server_type="Proxy Server")
			agent.new_upstream_code_server(self.server, self.name)

			agent = Agent(self.server, server_type="Server")
			agent.setup_code_server(self.bench, self.name)
		except Exception as e:
			log_error(title="Setup Code Server Failed", data=e)


def process_new_code_server_job_update(job):
	other_job_types = {
		"Add Code Server to Upstream": ("Setup Code Server"),
		"Setup Code Server": ("Add Code Server to Upstream"),
	}[job.job_type]

	first = job.status
	second = frappe.get_all(
		"Agent Job",
		fields=["status"],
		filters={"job_type": ("in", other_job_types), "code_server": job.code_server},
	)[0].status

	if "Success" == first == second:
		updated_status = "Running"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	else:
		updated_status = "Pending"

	frappe.db.set_value("Code Server", job.code_server, "status", updated_status)
