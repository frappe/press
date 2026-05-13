# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from datetime import datetime


def create_test_remote_file(
	site: str | None = None,
	creation: datetime | None = None,
	file_path: str | None = None,
	file_size: int = 1024,
):
	"""Create test remote file doc for required timestamp."""
	creation = creation or frappe.utils.now_datetime()
	remote_file = frappe.get_doc(
		{
			"doctype": "Remote File",
			"status": "Available",
			"site": site,
			"file_path": file_path,
			"file_size": file_size,
		}
	).insert(ignore_if_duplicate=True)
	remote_file.db_set("creation", creation)
	remote_file.reload()
	return remote_file


class TestRemoteFile(FrappeTestCase):
	pass
