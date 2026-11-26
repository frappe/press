# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import cast

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.backup_bucket.backup_bucket import BackupBucket
from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.site_backup.site_backup import get_backup_bucket


def create_test_backup_bucket(bucket_name: str, region: str = "ap-south-1") -> BackupBucket:
	if frappe.db.exists("Backup Bucket", bucket_name):
		return BackupBucket("Backup Bucket", bucket_name)
	bucket = frappe.get_doc(
		{
			"doctype": "Backup Bucket",
			"bucket_name": bucket_name,
			"region": region,
			"endpoint_url": f"https://s3.{region}.amazonaws.com",
		}
	)
	return cast("BackupBucket", bucket.insert(ignore_permissions=True))


def create_generic_cluster(name: str, backup_bucket: str | None) -> Cluster:
	cluster = frappe.get_doc(
		{"doctype": "Cluster", "name": name, "cloud_provider": "Generic", "backup_bucket": backup_bucket}
	)
	return cast("Cluster", cluster.insert(ignore_permissions=True))


class TestBackupBucket(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_clusters_that_share_a_bucket_both_back_up_to_that_bucket(self):
		bucket = create_test_backup_bucket("shared.backups.test", "eu-central-1")
		create_generic_cluster("Shared A", bucket.name)
		create_generic_cluster("Shared B", bucket.name)

		for cluster in ("Shared A", "Shared B"):
			config = get_backup_bucket(cluster, region=True)
			self.assertEqual(
				(config["name"], config["region"], config["endpoint_url"]),
				("shared.backups.test", "eu-central-1", "https://s3.eu-central-1.amazonaws.com"),
			)

	def test_backup_of_a_cluster_without_a_bucket_fails_instead_of_using_the_press_settings_bucket(self):
		cluster = create_generic_cluster("Legacy", create_test_backup_bucket("legacy.backups.test").name)
		cluster.db_set("backup_bucket", None)
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "fallback.backups.test")

		with self.assertRaisesRegex(frappe.MandatoryError, "Set the Backup Bucket of cluster Legacy"):
			get_backup_bucket("Legacy")

	def test_new_cluster_without_a_backup_bucket_is_rejected(self):
		with self.assertRaisesRegex(frappe.MandatoryError, "backup_bucket"):
			create_generic_cluster("No Bucket", None)

		self.assertFalse(frappe.db.exists("Cluster", "No Bucket"))

	def test_existing_cluster_without_a_backup_bucket_cannot_be_saved(self):
		cluster = create_generic_cluster("Old", create_test_backup_bucket("old.backups.test").name)
		cluster.db_set("backup_bucket", None)

		with self.assertRaisesRegex(frappe.MandatoryError, "backup_bucket"):
			Cluster("Cluster", "Old").save(ignore_permissions=True)

	def test_patch_gives_clusters_without_a_bucket_the_press_settings_bucket(self):
		from press.patches.v0_8_0 import set_missing_cluster_backup_buckets

		own_bucket = create_test_backup_bucket("own.backups.test").name
		create_generic_cluster("Has Bucket", own_bucket)
		create_generic_cluster("No Bucket", own_bucket).db_set("backup_bucket", None)
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "settings.backups.test")
		frappe.db.set_single_value("Press Settings", "backup_region", "ap-south-1")

		set_missing_cluster_backup_buckets.execute()
		# A second run finds the bucket record and no cluster to update
		set_missing_cluster_backup_buckets.execute()

		self.assertEqual(
			frappe.db.get_value("Cluster", "No Bucket", "backup_bucket"), "settings.backups.test"
		)
		self.assertEqual(frappe.db.get_value("Cluster", "Has Bucket", "backup_bucket"), own_bucket)
		self.assertEqual(
			frappe.db.get_value("Backup Bucket", "settings.backups.test", "region"), "ap-south-1"
		)

	def test_agent_sends_no_offsite_config_for_a_cluster_without_a_bucket(self):
		from press.agent import Agent

		cluster = create_generic_cluster("Legacy", create_test_backup_bucket("legacy.backups.test").name)
		cluster.db_set("backup_bucket", None)

		self.assertIsNone(Agent("agent.test")._get_offsite_backup_config("Legacy", "path"))


OCI_ENDPOINT = "https://namespace.compat.objectstorage.me-jeddah-1.oraclecloud.com"


def set_oci_keys():
	frappe.db.set_single_value("Press Settings", "oci_offsite_backups_access_key_id", "oci-access-key")
	settings = frappe.get_single("Press Settings")
	settings.oci_offsite_backups_secret_access_key = "oci-secret-key"
	settings.save(ignore_permissions=True)


def new_oci_bucket(endpoint_url: str = OCI_ENDPOINT):
	return frappe.get_doc(
		{
			"doctype": "Backup Bucket",
			"bucket_name": "oci.jeddah.backups.test",
			"provider": "OCI",
			"region": "me-jeddah-1",
			"endpoint_url": endpoint_url,
		}
	)


class TestOCIBackupBucket(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_oci_bucket_is_rejected_until_press_settings_has_the_oci_keys(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Set the OCI offsite backup keys"):
			new_oci_bucket().insert(ignore_permissions=True)

	def test_oci_bucket_with_an_endpoint_of_another_region_is_rejected(self):
		set_oci_keys()
		endpoint = "https://namespace.compat.objectstorage.sa-saopaulo-1.oraclecloud.com"

		with self.assertRaisesRegex(
			frappe.ValidationError,
			"must be https://NAMESPACE.compat.objectstorage.me-jeddah-1.oraclecloud.com",
		):
			new_oci_bucket(endpoint).insert(ignore_permissions=True)

	def test_oci_bucket_with_replication_is_rejected(self):
		set_oci_keys()
		bucket = new_oci_bucket()
		bucket.update(
			{
				"replication_enabled": 1,
				"replication_bucket": "replica",
				"replication_region": "me-riyadh-1",
				"replication_endpoint_url": OCI_ENDPOINT,
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Replication is not supported for OCI"):
			bucket.insert(ignore_permissions=True)

	def test_agent_gets_the_oci_keys_and_endpoint_for_a_cluster_with_an_oci_bucket(self):
		from press.agent import Agent

		set_oci_keys()
		bucket = new_oci_bucket().insert(ignore_permissions=True)
		create_generic_cluster("OCI Jeddah Test", bucket.name)

		auth = Agent("agent.test")._get_offsite_backup_config("OCI Jeddah Test", "path")["auth"]

		self.assertEqual(
			(auth["ACCESS_KEY"], auth["SECRET_KEY"], auth["PROVIDER"], auth["ENDPOINT_URL"]),
			("oci-access-key", "oci-secret-key", "OCI", OCI_ENDPOINT),
		)

	def test_aws_bucket_still_gets_the_aws_keys_when_oci_keys_are_set(self):
		from press.press.doctype.backup_bucket.backup_bucket import (
			get_bucket_credentials,
			get_provider_credentials,
		)

		set_oci_keys()
		bucket = create_test_backup_bucket("aws.mumbai.backups.test")

		self.assertEqual(get_bucket_credentials(bucket.name), get_provider_credentials("AWS S3"))
		self.assertNotEqual(get_bucket_credentials(bucket.name)[0], "oci-access-key")
