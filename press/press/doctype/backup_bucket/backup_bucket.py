# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

# The Press Settings fields that hold each provider's access key and secret key
PROVIDER_KEY_FIELDS = {
	"AWS S3": ("offsite_backups_access_key_id", "offsite_backups_secret_access_key"),
	"OCI": ("oci_offsite_backups_access_key_id", "oci_offsite_backups_secret_access_key"),
}


class BackupBucket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bucket_name: DF.Data | None
		endpoint_url: DF.Data | None
		provider: DF.Literal["AWS S3", "OCI"]
		region: DF.Data | None
		replication_bucket: DF.Data | None
		replication_enabled: DF.Check
		replication_endpoint_url: DF.Data | None
		replication_region: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if self.provider == "OCI":
			self.validate_oci_endpoint()
			self.validate_oci_replication()
			self.validate_provider_keys()

	def validate_oci_endpoint(self):
		expected = f".compat.objectstorage.{self.region}.oraclecloud.com"
		if not (self.endpoint_url or "").rstrip("/").endswith(expected):
			frappe.throw(
				_("Endpoint URL of an OCI bucket must be https://NAMESPACE{0}").format(expected),
				frappe.ValidationError,
			)

	def validate_oci_replication(self):
		# Reads from a replica use the AWS keys, so OCI buckets can't replicate yet
		if self.replication_enabled:
			frappe.throw(_("Replication is not supported for OCI buckets"), frappe.ValidationError)

	def validate_provider_keys(self):
		if not get_provider_credentials(self.provider):
			frappe.throw(
				_("Set the {0} offsite backup keys in Press Settings first").format(self.provider),
				frappe.ValidationError,
			)


def get_bucket_credentials(bucket_name: str, raise_exception: bool = True) -> tuple[str, str] | None:
	"""The access key and secret key for a bucket, picked by the bucket's provider.

	A bucket that is not a Backup Bucket, like the one in Press Settings, is on AWS.
	"""
	provider = frappe.db.get_value("Backup Bucket", bucket_name, "provider") or "AWS S3"
	credentials = get_provider_credentials(provider)
	if not credentials and raise_exception:
		frappe.throw(_("Set the {0} offsite backup keys in Press Settings").format(provider))
	return credentials


def get_provider_credentials(provider: str) -> tuple[str, str] | None:
	key_field, secret_field = PROVIDER_KEY_FIELDS[provider]
	access_key = frappe.db.get_single_value("Press Settings", key_field)
	secret_key = get_decrypted_password(
		"Press Settings", "Press Settings", secret_field, raise_exception=False
	)
	if not (access_key and secret_key):
		return None
	return access_key, secret_key


def get_replication_target(bucket_name: str) -> dict | None:
	"""Where reads go once a bucket replicates, or None when it doesn't.

	Backups are written to the primary and replicated out, so the replica is what still
	holds an object the primary's lifecycle rules have already expired.
	"""
	if not frappe.db.exists("Backup Bucket", bucket_name):
		return None

	bucket = BackupBucket("Backup Bucket", bucket_name)
	if not bucket.replication_enabled:
		return None

	return {
		"name": bucket.replication_bucket,
		"region": bucket.replication_region,
		"endpoint_url": bucket.replication_endpoint_url,
	}
