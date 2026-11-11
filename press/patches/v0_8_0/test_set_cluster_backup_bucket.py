import frappe
from frappe.database.schema import add_column
from frappe.tests.utils import FrappeTestCase

from press.patches.v0_8_0.set_cluster_backup_bucket import execute
from press.press.doctype.backup_bucket.test_backup_bucket import (
	create_generic_cluster,
	create_test_backup_bucket,
)


class TestSetClusterBackupBucket(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Sites installed after the field was removed never had the column; add it as old sites have it
		if not frappe.db.has_column("Backup Bucket", "cluster"):
			add_column("Backup Bucket", "cluster", "Link")
			# add_column keeps the cached column list, so has_column in the patch would miss the new column
			assert frappe.client_cache is not None
			frappe.client_cache.delete_value("table_columns::tabBackup Bucket")

	def tearDown(self):
		frappe.db.rollback()

	def given_bucket_of_cluster(self, bucket_name: str, cluster: str | None, modified: str):
		create_test_backup_bucket(bucket_name)
		frappe.db.sql(
			"update `tabBackup Bucket` set cluster = %s, modified = %s where name = %s",
			(cluster, modified, bucket_name),
		)

	def cluster_buckets(self) -> dict:
		return dict(frappe.get_all("Cluster", fields=["name", "backup_bucket"], as_list=True))

	def test_patch_sets_each_cluster_to_the_bucket_that_named_it(self):
		create_generic_cluster("Patch A", create_test_backup_bucket("placeholder.backups.test").name)
		frappe.db.set_value("Cluster", "Patch A", "backup_bucket", None)
		self.given_bucket_of_cluster("patch-a.backups.test", "Patch A", "2024-01-01")

		execute()

		self.assertEqual(frappe.db.get_value("Cluster", "Patch A", "backup_bucket"), "patch-a.backups.test")

	def test_patch_picks_the_last_modified_bucket_when_two_name_the_same_cluster(self):
		create_generic_cluster("Patch B", create_test_backup_bucket("placeholder.backups.test").name)
		self.given_bucket_of_cluster("older.backups.test", "Patch B", "2023-01-01")
		self.given_bucket_of_cluster("newer.backups.test", "Patch B", "2024-01-01")

		execute()

		self.assertEqual(frappe.db.get_value("Cluster", "Patch B", "backup_bucket"), "newer.backups.test")

	def test_patch_leaves_every_cluster_alone_for_a_bucket_whose_cluster_no_longer_exists(self):
		frappe.db.sql("update `tabBackup Bucket` set cluster = null")
		self.given_bucket_of_cluster("orphan.backups.test", "Deleted Cluster", "2024-01-01")
		before = self.cluster_buckets()

		execute()

		self.assertEqual(self.cluster_buckets(), before)
		self.assertFalse(frappe.db.exists("Cluster", "Deleted Cluster"))
