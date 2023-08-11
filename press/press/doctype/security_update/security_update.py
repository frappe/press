# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error
import re
from frappe.utils import now_datetime


class SecurityUpdate(Document):
	@staticmethod
	def fetch_security_updates(server_obj):
		"""Fetch security updates"""
		try:
			ansible = Ansible(
				playbook="security_update.yml",
				server=server_obj,
			)
			play = ansible.run()
			if play.status == "Success":
				package_list = SecurityUpdate._prepare_package_list(ansible.play)
				SecurityUpdate._fetch_package_meta(package_list, server_obj)

		except Exception:
			log_error("Fetch security updates exception", server=server_obj.as_dict())

	@staticmethod
	def _prepare_package_list(play):
		packages = []
		filters = {"task": "Fetch packages due for security updates", "play": play}
		packages_str = frappe.db.get_value("Ansible Task", filters, "output")

		if packages_str:
			for package_string in packages_str.split("\n"):
				package_name = package_string.split("/")[0]

				if package_name == "Listing...":
					continue

				packages.append(package_name)

		return packages

	@staticmethod
	def _fetch_package_meta(package_list, server_obj):
		package_list = package_list[:6]

		for package in package_list:
			try:
				ansible = Ansible(
					playbook="security_update.yml",
					server=server_obj,
					variables={"fetch_package_meta": True, "package": package},
				)
				play = ansible.run()
				if play.status == "Success":
					SecurityUpdate._create_security_update(package, ansible.play, server_obj)
			except Exception:
				log_error("Fetch package meta exception", server=server_obj.as_dict())

	@staticmethod
	def _create_security_update(package, play, server_obj):
		package_meta = SecurityUpdate.get_package_meta_from_log(play)
		package_change_log = SecurityUpdate.get_package_change_log(play)
		version = SecurityUpdate.get_package_version(package_meta)
		priority, level = SecurityUpdate.get_package_priority(package_meta)

		if frappe.db.exists(
			"Security Update",
			{"package": package, "server": server_obj.name, "version": version},
		):
			return

		try:
			security_update = frappe.new_doc("Security Update")
			security_update.update(
				{
					"package": package,
					"server_type": server_obj.doctype,
					"server": server_obj.name,
					"package_meta": package_meta,
					"change_log": package_change_log,
					"version": version,
					"priority": priority,
					"datetime": now_datetime(),
					"priority_level": level,
				}
			)
			security_update.insert(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			log_error("Create security update exception", server=server_obj.as_dict())

	@staticmethod
	def get_package_meta_from_log(play):
		filters = {"task": "Fetch package meta", "play": play}
		package_meta_str = frappe.db.get_value("Ansible Task", filters, "output")

		if package_meta_str:
			return package_meta_str

		return None

	@staticmethod
	def get_package_change_log(play):
		filters = {"task": "Fetch package change log", "play": play}
		package_change_log = frappe.db.get_value("Ansible Task", filters, "output")

		if package_change_log:
			return package_change_log

		return None

	@staticmethod
	def get_package_version(package_meta):
		version = re.search("Version:(.*)", package_meta)

		try:
			return version.group(1)
		except Exception:
			pass

		return None

	@staticmethod
	def get_package_priority_and_level(package_meta):
		priority_mapper = {"required": "High", "standard": "Medium", "optional": "Low"}
		priority_level_mapper = {"High": 1, "Medium": 2, "Low": 3}
		priority = re.search("Priority:(.*)", package_meta)

		try:
			priority = priority_mapper.get(priority.group(1).strip(), "Low")
			priority_level = priority_level_mapper.get(priority, 3)

			return priority, priority_level
		except Exception:
			pass

		return "Low", 3
