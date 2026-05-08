# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# Cluster registries are utilizing harbor and therefore require
# A seperate controller model for them to address the configs
from __future__ import annotations

import hashlib
import typing

import frappe

from press.press.doctype.cluster_registry.cluster_registry_api import ClusterRegistryAPI
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.cluster_bucket.cluster_bucket import ClusterBucket
	from press.press.doctype.tls_certificate.tls_certificate import TLSCertificate


class ClusterRegistry(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		admin_password: DF.Password | None
		cluster: DF.Link | None
		domain: DF.Link | None
		hostname: DF.Data | None
		ip: DF.Data | None
		is_retention_policy_set: DF.Check
		is_setup: DF.Check
		number_of_days: DF.Int
		private_ip: DF.Data | None
		project: DF.Data | None
		provider: DF.Data | None
		retention_execution_cron: DF.Data | None
		retention_policy: DF.Literal["Push", "Pull"]
		secret: DF.Password | None
		status: DF.Literal["GC", "Active", "Broken", "Pending"]
		storage_bucket: DF.Link | None
		user: DF.Data | None
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_cluster()

	def client(self) -> ClusterRegistryAPI:
		if self.status != "Active":
			raise Exception("Cluster registry is not active")

		return ClusterRegistryAPI(
			harbor_url=f"https://{self.name}", harbor_admin_password=self.get_password("admin_password")
		)

	def get_bucket_access_credentials(self) -> tuple[str, str]:
		"""Fetches the access key and secret key for the S3 bucket associated with this registry"""
		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		provider = cluster.cloud_provider

		credentials_map = {
			"AWS EC2": ("aws_access_key_id", "aws_secret_access_key"),
			"Hetzner": ("hetzner_access_key_id", "hetzner_secret_access_key"),
			"DigitalOcean": ("digital_ocean_access_key_id", "digital_ocean_secret_access_key"),
			"OCI": ("oci_access_key_id", "oci_secret_access_key"),
		}

		if provider in credentials_map:
			access_key_field, secret_key_field = credentials_map[provider]
			return (
				getattr(cluster, access_key_field),  # This is not a password!
				cluster.get_password(secret_key_field),
			)

		raise ValueError(f"Unsupported cloud provider: {provider}")

	def make_or_get_s3_bucket_for_registry(self) -> ClusterBucket:
		"""Make a cluster bucket for this registry if it doesn't exist and return it
		The issue here is that some cloud providers (hetzner...) require globally unique bucket names therefore we generate
		hashes based on the name on the fly and we need to ensure that we fetch the correct bucket if it already exists.
		"""
		cloud_provider = frappe.db.get_value("Cluster", self.cluster, "cloud_provider")
		base_bucket_name = f"frappe-cloud-{self.cluster}-registry"
		hash_suffix = hashlib.sha256(base_bucket_name.encode()).hexdigest()[:8]

		bucket_name = (
			base_bucket_name if cloud_provider != "Hetzner" else base_bucket_name + "-" + hash_suffix
		)
		bucket_name = bucket_name.casefold().replace(" ", "-")

		if not frappe.db.exists(
			"Cluster Bucket",
			{
				"cluster": self.cluster,
				"bucket_name": bucket_name,
			},
		):
			# Insert if not present (after insert takes care of provisioning)
			cluster_bucket: ClusterBucket = frappe.get_doc(
				{
					"doctype": "Cluster Bucket",
					"cluster": self.cluster,
					"bucket_name": bucket_name,
				},
			).insert()
		else:
			cluster_bucket = frappe.get_doc(
				"Cluster Bucket",
				{"cluster": self.cluster, "bucket_name": bucket_name},
			)

		return cluster_bucket

	def _setup_cluster_registry(self):
		tls_certificate: TLSCertificate = frappe.get_doc(
			"TLS Certificate", {"wildcard": True, "status": "Active", "domain": self.domain}
		)
		cluster_bucket = self.make_or_get_s3_bucket_for_registry()
		access_key, secret_key = self.get_bucket_access_credentials()

		try:
			ansible = Ansible(
				playbook="cluster_registry.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"harbor_hostname": self.name,
					"fullchain": tls_certificate.full_chain,
					"private_key": tls_certificate.private_key,
					"admin_password": self.get_password("admin_password"),
					"s3_region": cluster_bucket.region,
					"s3_bucket": cluster_bucket.bucket_name,
					"s3_region_endpoint": cluster_bucket.endpoint_url,
					"s3_access_key": access_key,
					"s3_secret_key": secret_key,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_setup = True
				self.storage_bucket = cluster_bucket.name
			else:
				self.status = "Broken"
		except Exception as e:
			self.status = "Broken"
			log_error(f"Error while provisioning cluster registry {e}")
		finally:
			self.save()

	def setup_server(self):
		self.create_dns_record()
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_cluster_registry",
			queue="long",
			timeout=3600,
		)

	def create_project(self):
		"""Create a project for this cluster registry"""
		project_name = f"frappe-cloud-production-{self.name}".casefold().replace(
			" ", "-"
		)  # They expect only lowercase and dashes
		try:
			self.client().create_project(project_name)
		except Exception as e:
			print(f"Error while creating project for cluster registry {e}")

		self.project = project_name
		self.save()

	def create_storage_quota(self):
		"""Set storage quota for this cluster registry project based on the disk size"""
		disk_size = frappe.db.get_value("Virtual Machine", self.virtual_machine, "disk_size")
		try:
			self.client().create_project_quota(self.project, int(disk_size))
		except Exception as e:
			print(f"Error while setting storage quota for cluster registry {e}")

	def create_project_robot(self):
		"""Create a robot account for this cluster registry"""
		try:
			name, secret = self.client().create_project_robot(
				self.project,
				robot_name="frappe-cloud-robot",
			)
			if name and secret:
				self.user = name
				self.secret = secret
			self.save()
		except Exception as e:
			print(f"Error while creating project robot for cluster registry {e}")

	def create_retention_policy(self):
		"""Create a retention policy for this cluster registry"""
		try:
			self.client().create_retention_rule(
				self.project,
				older_than_days=self.number_of_days,
				pushed_based_retention=self.retention_policy == "Push",
			)
			self.is_retention_policy_set = True
			self.save()
		except Exception as e:
			print(f"Error while creating retention policy for cluster registry {e}")

	@frappe.whitelist()
	def setup_project(self):
		"""Create a project for this cluster registry"""
		self.create_project()
		self.create_storage_quota()
		self.create_project_robot()
		# This is questionable (Maybe we need to pass this logic to `archive_benchmark`)
		self.create_retention_policy()

	@frappe.whitelist()
	def trigger_retention_policy(self):
		"""Manually trigger a retention policy execution for this cluster registry"""
		if not self.is_retention_policy_set:
			frappe.throw("Project is not setup yet")

		try:
			self.client().trigger_retention_execution(self.project)
		except Exception as e:
			log_error(f"Error while triggering retention policy for cluster registry {e}")
