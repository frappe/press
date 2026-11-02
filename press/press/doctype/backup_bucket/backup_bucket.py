# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class BackupBucket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bucket_name: DF.Data | None
		cluster: DF.Link | None
		endpoint_url: DF.Data | None
		region: DF.Data | None
		replication_bucket: DF.Data | None
		replication_enabled: DF.Check
		replication_endpoint_url: DF.Data | None
		replication_region: DF.Data | None
	# end: auto-generated types


def get_replication_target(bucket_name: str) -> dict | None:
	"""Where reads go once a bucket replicates, or None when it doesn't.

	Backups are written to the primary and replicated out, so the replica is what still
	holds an object the primary's lifecycle rules have already expired.
	"""
	if not frappe.db.exists("Backup Bucket", bucket_name):
		return None

	bucket: BackupBucket = frappe.get_doc("Backup Bucket", bucket_name)
	if not bucket.replication_enabled:
		return None

	return {
		"name": bucket.replication_bucket,
		"region": bucket.replication_region,
		"endpoint_url": bucket.replication_endpoint_url,
	}
