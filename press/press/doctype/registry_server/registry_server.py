# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import os

import frappe
from frappe.frappeclient import FrappeClient

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class RegistryServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_password: DF.Password | None
		bucket_name: DF.Data | None
		container_registry_config_path: DF.Data | None
		docker_data_mountpoint: DF.Data | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		is_mirror: DF.Check
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		plan: DF.Link | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		proxy_pass: DF.Data | None
		region: DF.Data | None
		region_endpoint: DF.Data | None
		registry_password: DF.Password | None
		registry_username: DF.Data | None
		root_public_key: DF.Code | None
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tls_certificate_renewal_failed: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_agent_password()
		self.validate_registry_username()
		self.validate_registry_password()
		self.validate_monitoring_password()

	def validate_registry_password(self):
		if not self.registry_password:
			self.registry_password = frappe.generate_hash(length=32)

	def validate_registry_username(self):
		if not self.registry_username:
			self.registry_username = "frappe"

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def _setup_server(self):
		settings = frappe.get_cached_doc("Press Settings")
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		monitoring_password = self.get_password("monitoring_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		access_key = settings.docker_s3_access_key
		secret_key = settings.get_password("docker_s3_secret_key")
		variables = {
			"server": self.name,
			"workers": 1,
			"domain": self.domain,
			"agent_password": agent_password,
			"agent_repository_url": agent_repository_url,
			"monitoring_password": monitoring_password,
			"private_ip": self.private_ip,
			"registry_username": self.registry_username,
			"registry_password": self.get_password("registry_password"),
			"certificate_private_key": certificate.private_key,
			"certificate_full_chain": certificate.full_chain,
			"is_mirror": self.is_mirror,
			"docker_data_mountpoint": self.docker_data_mountpoint,
			"certificate_intermediate_chain": certificate.intermediate_chain,
			"container_registry_config_path": self.container_registry_config_path,
			"registry_url": f"https://{self.name}",
			"access_key": access_key,
			"secret_key": secret_key,
			"region_endpoint": self.region_endpoint,
			"region": self.region,
			"bucket_name": self.bucket_name,
			"proxy_pass": self.proxy_pass,
		}
		try:
			ansible = Ansible(
				playbook="registry.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables=variables,
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Registry Server Setup Exception", server=self.as_dict())

		self.save()

	def prune_mirror_registry(self):
		"""Clear out the docker system for the mirror registry"""
		if not self.is_mirror:
			return

		frappe.enqueue_doc(self.doctype, self.name, "_prune_mirror_registry", queue="long", timeout=3600)

	def _prune_mirror_registry(self):
		try:
			ansible = Ansible(
				playbook="prune_mirror_registry.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mountpoint": os.path.join(
						self.docker_data_mountpoint, "docker", "registry", "v2", "blobs"
					),
					"registry_container": "registry-registry-1",
				},
			)
			ansible.run()
		except Exception:
			log_error("Mirror Registry Prune Failed", server=self.as_dict())

	@frappe.whitelist()
	def show_registry_password(self):
		"""Show registry password"""
		frappe.msgprint(self.get_password("registry_password"))

	@frappe.whitelist()
	def create_registry_mirror(
		self,
		hostname: str,
		docker_data_mountpoint: str,
		container_registry_config_path: str,
		public_ip: str,
		private_ip: str,
		proxy_pass: str,
	):
		"""Create a registry mirror"""
		registry: RegistryServer = frappe.get_doc(
			{
				"doctype": "Registry Server",
				"ip": public_ip,
				"private_ip": private_ip,
				"docker_data_mountpoint": docker_data_mountpoint,
				"container_registry_config_path": container_registry_config_path,
				"hostname": hostname,
				"is_mirror": True,
				"provider": "Generic",
				"registry_username": self.registry_username,
				"registry_password": self.get_password("registry_password"),
				"proxy_pass": proxy_pass,
			}
		)
		registry.insert()

	def _rewrite_config(self):
		try:
			ansible = Ansible(
				playbook="rewrite_registry_config.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"is_mirror": self.is_mirror,
					"proxy_pass": self.proxy_pass,
					"docker_data_mountpoint": self.docker_data_mountpoint,
					"container_registry_config_path": self.container_registry_config_path,
					"registry_username": self.registry_username,
					"registry_password": self.get_password("registry_password"),
				},
			)
			ansible.run()
		except Exception as e:
			log_error("Error during mirror config rewrite", e)

	@frappe.whitelist()
	def rewrite_config(self):
		"""Rewrite mirror's config"""
		if not self.is_mirror:
			frappe.throw("Config can not be update for the hub registry")

		frappe.enqueue_doc(self.doctype, self.name, "_rewrite_config")


def delete_old_images_from_registry():  # noqa: C901
	"""Purge registry of older images"""
	settings = frappe.get_doc("Press Settings", None)
	registry = settings.docker_registry_url

	requests = FrappeClient(registry).session

	headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
	auth = (settings.docker_registry_username, settings.docker_registry_password)

	# Traverse all pages
	last = None
	while True:
		params = {"last": last} if last else {}
		response = requests.get(f"https://{registry}/v2/_catalog", auth=auth, headers=headers, params=params)

		if not response.ok:
			return

		repositories = response.json()["repositories"]
		if not repositories:
			break
		last = repositories[-1]

		for repository in repositories:
			try:
				# Skip non-bench images
				if not frappe.db.exists("Release Group", repository.split("/")[-1]):
					continue
				tags = (
					requests.get(f"https://{registry}/v2/{repository}/tags/list", auth=auth, headers=headers)
					.json()
					.get("tags", [])
					or []
				)
				tags = sorted(tags)
				for tag in tags:
					if tag.startswith("deploy-"):
						deploy_candidate = tag
					else:
						deploy_candidate = frappe.db.get_value(
							"Deploy Candidate Build", tag, "deploy_candidate"
						)

					if not deploy_candidate:
						in_use = False
					else:
						in_use = frappe.db.get_all(
							"Bench",
							["count(*) as count"],
							{"status": "Active", "candidate": deploy_candidate},
						)[0].count

					if not in_use:
						digest = requests.head(
							f"https://{registry}/v2/{repository}/manifests/{tag}", auth=auth, headers=headers
						).headers["Docker-Content-Digest"]
						should_delete = False

						# Delete all except the most recent candidates
						if tags.index(tag) < len(tags) - 1:
							should_delete = True
						else:
							# For most recent candidate delete the image if
							# 1. It hasn't been in use for sometime OR
							# 2. The Release Group is disabled

							enabled = frappe.db.get_value(
								"Release Group", repository.split("/")[-1], "enabled"
							)
							created = frappe.db.get_value("Deploy Candidate", deploy_candidate, "creation")
							if not enabled or created < frappe.utils.add_days(None, -7):
								# log(["DELETING", repository, tag, tags.index(tag) == len(tags) - 1, not enabled, created])
								should_delete = True

						if should_delete:
							# DELETE the image
							requests.delete(
								f"https://{registry}/v2/{repository}/manifests/{digest}",
								auth=auth,
								headers=headers,
							)

			except Exception:
				pass
