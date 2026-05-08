# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import hashlib
import typing

import boto3
import frappe
import oci
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster


class ClusterBucket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bucket_name: DF.Data
		bucket_url: DF.Data | None
		cluster: DF.Link
		endpoint_url: DF.Data | None
		namespace: DF.Data | None
		region: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		provider = frappe.db.get_value("Cluster", self.cluster, "cloud_provider")
		if provider == "Hetzner":
			self.bucket_name = (
				f"{self.bucket_name}-{hashlib.sha256(self.bucket_name.encode()).hexdigest()[:8]}"
			)

	def after_insert(self):
		self.provision()

	def provision(self):
		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		cls: (
			AWSClusterBucketProvisioner
			| OCIClusterBucketProvisioner
			| HetznerClusterBucketProvisioner
			| DigitalOceanClusterBucketProvisioner
		) = PROVISIONERS.get(cluster.cloud_provider)

		if not cls:
			frappe.throw(f"Unsupported cloud provider: {cluster.cloud_provider}")

		fields = cls().provision(self.name, cluster)

		# Explicitly setting the name here since the provider recommended a new name
		if "name" in fields:
			self.name = fields.pop("name")

		for key, value in fields.items():
			setattr(self, key, value)

		self.save()


class AWSClusterBucketProvisioner:
	def provision(self, name: str, cluster: Cluster):
		s3 = boto3.client(
			"s3",
			region_name=cluster.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

		assert cluster.region
		kwargs: dict[str, str | dict[str, str]] = {"Bucket": name}
		if cluster.region != "us-east-1":
			kwargs["CreateBucketConfiguration"] = {"LocationConstraint": cluster.region}

		s3.create_bucket(**kwargs)
		s3.put_public_access_block(
			Bucket=name,
			PublicAccessBlockConfiguration={
				"BlockPublicAcls": True,
				"IgnorePublicAcls": True,
				"BlockPublicPolicy": True,
				"RestrictPublicBuckets": True,
			},
		)

		return {
			"region": cluster.region,
			"endpoint_url": f"https://s3.{cluster.region}.amazonaws.com",
			"bucket_url": f"https://{name}.s3.{cluster.region}.amazonaws.com",
		}


class HetznerClusterBucketProvisioner:
	def provision(self, name: str, cluster: Cluster):
		endpoint_url = f"https://{cluster.region}.your-objectstorage.com"
		s3 = boto3.client(
			"s3",
			region_name=cluster.region,
			endpoint_url=endpoint_url,
			aws_access_key_id=cluster.get_password("hetzner_access_key_id"),
			aws_secret_access_key=cluster.get_password("hetzner_secret_access_key"),
		)
		s3.create_bucket(Bucket=name)

		return {
			"region": cluster.region,
			"endpoint_url": endpoint_url,
			"bucket_url": f"{endpoint_url}/{name}",
			"name": name,
		}


class DigitalOceanClusterBucketProvisioner:
	def provision(self, name: str, cluster: Cluster):
		endpoint_url = f"https://{cluster.region}.digitaloceanspaces.com"
		s3 = boto3.client(
			"s3",
			region_name=cluster.region,
			endpoint_url=endpoint_url,
			aws_access_key_id=cluster.get_password("digital_ocean_access_key_id"),
			aws_secret_access_key=cluster.get_password("digital_ocean_secret_access_key"),
		)
		s3.create_bucket(Bucket=name)

		return {
			"region": cluster.region,
			"endpoint_url": endpoint_url,
			"bucket_url": f"https://{name}.{cluster.region}.digitaloceanspaces.com",
		}


class OCIClusterBucketProvisioner:
	def provision(self, name: str, cluster: Cluster):
		config = cluster.get_oci_config()
		object_storage = oci.object_storage.ObjectStorageClient(config)
		namespace = object_storage.get_namespace().data

		object_storage.create_bucket(
			namespace_name=namespace,
			compartment_id=cluster.oci_tenancy,
			create_bucket_details=oci.object_storage.models.CreateBucketDetails(
				name=name,
				compartment_id=cluster.oci_tenancy,
				public_access_type="NoPublicAccess",
			),
		)

		return {
			"region": cluster.region,
			"namespace": namespace,
			"endpoint_url": f"https://objectstorage.{cluster.region}.oraclecloud.com",
			"bucket_url": f"https://objectstorage.{cluster.region}.oraclecloud.com/n/{namespace}/b/{name}/o/",
		}


PROVISIONERS = {
	"AWS EC2": AWSClusterBucketProvisioner,
	"Hetzner": HetznerClusterBucketProvisioner,
	"DigitalOcean": DigitalOceanClusterBucketProvisioner,
	"OCI": OCIClusterBucketProvisioner,
}
