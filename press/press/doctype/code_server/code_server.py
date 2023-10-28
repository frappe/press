# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists

from press.agent import Agent
from press.utils import log_error
from press.utils.dns import create_dns_record, _change_dns_record


class CodeServer(Document):
	def autoname(self):
		self.name = self.subdomain + "." + self.domain

	def validate(self):
		if self.has_value_changed("subdomain"):
			if frappe.db.exists("Code Server", self.name):
				frappe.throw(
					f"Code Server {self.name} already exists please choose a different name"
				)
			if frappe.db.exists(
				"Code Server", {"bench": self.bench, "status": ("!=", "Archived")}
			):
				frappe.throw(
					"Code Server already exists for selected bench choose a different bench"
				)
		if not self.proxy_server and self.has_value_changed("server"):
			self.proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")

	def after_insert(self):
		self.setup()

	@frappe.whitelist()
	def setup(self):
		try:
			create_dns_record(doc=self, record_name=self.name)
			agent = Agent(self.proxy_server, server_type="Proxy Server")
			agent.new_upstream_file(server=self.server, code_server=self.name)

			self.password = frappe.generate_hash(length=40)
			agent = Agent(self.server, server_type="Server")
			agent.setup_code_server(self.bench, self.name, self.password)
			self.save(ignore_permissions=True)
		except Exception as e:
			log_error(title="Setup Code Server Failed", data=e)

	@frappe.whitelist()
	def stop(self):
		try:
			self.status = "Pending"
			agent = Agent(self.server, server_type="Server")
			agent.stop_code_server(self.bench, self.name)
		except Exception as e:
			log_error(title="Stop Code Server Failed", data=e)

	@frappe.whitelist()
	def start(self):
		try:
			self.status = "Pending"
			agent = Agent(self.server, server_type="Server")
			self.password = frappe.generate_hash(length=40)
			agent.start_code_server(self.bench, self.name, self.password)
			self.save(ignore_permissions=True)
		except Exception as e:
			log_error(title="Start Code Server Failed", data=e)

	@frappe.whitelist()
	def archive(self):
		try:
			self.status = "Pending"
			_change_dns_record(
				method="DELETE",
				domain=frappe.get_doc("Root Domain", self.domain),
				proxy_server=self.proxy_server,
				record_name=self.name,
			)
			agent = Agent(self.proxy_server, server_type="Proxy Server")
			agent.remove_upstream_file(server=self.server, code_server=self.name)

			agent = Agent(self.server, server_type="Server")
			agent.archive_code_server(self.bench, self.name)
			self.save(ignore_permissions=True)
		except Exception as e:
			log_error(title="Archive Code Server Failed", data=e)


def process_new_code_server_job_update(job):
	frappe.db.get_value("Code Server", job.code_server, "status")

	other_job_type = {
		"Add Code Server to Upstream": "Setup Code Server",
		"Setup Code Server": "Add Code Server to Upstream",
	}[job.job_type]

	first = job.status
	second = frappe.get_value(
		"Agent Job",
		{"job_type": other_job_type, "code_server": job.code_server},
		"status",
		for_update=True,
	)

	if "Success" == first == second:
		updated_status = "Running"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	else:
		updated_status = "Pending"

	frappe.db.set_value("Code Server", job.code_server, "status", updated_status)


def process_start_code_server_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Code Server", job.code_server, "status", "Running")


def process_stop_code_server_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Code Server", job.code_server, "status", "Stopped")


def process_archive_code_server_job_update(job):
	frappe.db.get_value("Code Server", job.code_server, "status")

	other_job_type = {
		"Remove Code Server from Upstream": "Archive Code Server",
		"Archive Code Server": "Remove Code Server from Upstream",
	}[job.job_type]

	first = job.status
	second = frappe.get_value(
		"Agent Job",
		{"job_type": other_job_type, "code_server": job.code_server},
		"status",
		for_update=True,
	)

	if "Success" == first == second:
		updated_status = "Archived"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	else:
		updated_status = "Pending"

	frappe.db.set_value("Code Server", job.code_server, "status", updated_status)
	if updated_status == "Archived":
		release_name(job.code_server)


def release_name(name):
	if ".archived" in name:
		return
	new_name = f"{name}.archived"
	new_name = append_number_if_name_exists("Code Server", new_name, separator=".")
	frappe.rename_doc("Code Server", name, new_name)
