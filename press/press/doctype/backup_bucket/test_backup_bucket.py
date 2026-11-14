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

	def test_cluster_without_a_bucket_backs_up_to_the_press_settings_bucket(self):
		cluster = create_generic_cluster("Legacy", create_test_backup_bucket("legacy.backups.test").name)
		cluster.db_set("backup_bucket", None)
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "fallback.backups.test")

		self.assertEqual(get_backup_bucket("Legacy"), "fallback.backups.test")

	def test_new_cluster_without_a_backup_bucket_is_rejected(self):
		with self.assertRaisesRegex(frappe.MandatoryError, "Set the Backup Bucket for the new cluster"):
			create_generic_cluster("No Bucket", None)

		self.assertFalse(frappe.db.exists("Cluster", "No Bucket"))

	def test_existing_cluster_without_a_backup_bucket_still_saves(self):
		cluster = create_generic_cluster("Old", create_test_backup_bucket("old.backups.test").name)
		cluster.db_set("backup_bucket", None)

		Cluster("Cluster", "Old").save(ignore_permissions=True)

		self.assertIsNone(frappe.db.get_value("Cluster", "Old", "backup_bucket"))
