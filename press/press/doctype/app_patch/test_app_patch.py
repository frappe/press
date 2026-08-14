# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_patch.app_patch import validate_patch

GIT_DIFF = """diff --git a/erpnext/hooks.py b/erpnext/hooks.py
index 1234567..89abcde 100644
--- a/erpnext/hooks.py
+++ b/erpnext/hooks.py
@@ -1,3 +1,4 @@
 import frappe
+import json

 app_name = "erpnext"
"""

FORMAT_PATCH = """From 89abcde0123456789 Mon Sep 17 00:00:00 2001
From: Someone <someone@example.com>
Date: Mon, 10 Aug 2026 12:00:00 +0530
Subject: [PATCH] Fix the thing

---
 erpnext/hooks.py | 1 +
 1 file changed, 1 insertion(+)

diff --git a/erpnext/hooks.py b/erpnext/hooks.py
--- a/erpnext/hooks.py
+++ b/erpnext/hooks.py
@@ -1,3 +1,4 @@
 import frappe
+import json
"""

PLAIN_DIFF = """--- old/hooks.py\t2026-08-10 12:00:00
+++ new/hooks.py\t2026-08-10 12:01:00
@@ -1 +1,2 @@
 import frappe
+import json
"""

NEW_FILE_DIFF = """diff --git a/erpnext/new.py b/erpnext/new.py
new file mode 100644
--- /dev/null
+++ b/erpnext/new.py
@@ -0,0 +1,2 @@
+import frappe
+
"""

BINARY_DIFF = """diff --git a/logo.png b/logo.png
index 1234567..89abcde 100644
GIT binary patch
literal 273
zcmV+s0q*_XP)<h;3K|Lk000e1NJLTq000mG000mO0ssI2kdbIM00009a7bBm000XU
"""


class TestValidatePatch(FrappeTestCase):
	"""The response body a patch URL returns has to parse as a diff before it is stored."""

	def tearDown(self):
		frappe.db.rollback()

	def test_git_diff_is_accepted(self):
		validate_patch(GIT_DIFF)

	def test_format_patch_output_is_accepted(self):
		validate_patch(FORMAT_PATCH)

	def test_plain_unified_diff_without_git_headers_is_accepted(self):
		validate_patch(PLAIN_DIFF)

	def test_diff_adding_a_new_file_is_accepted(self):
		validate_patch(NEW_FILE_DIFF)

	def test_git_binary_patch_is_accepted(self):
		"""It carries no @@ hunk, so it has to be recognised on its own."""
		validate_patch(BINARY_DIFF)

	def test_cloud_metadata_document_is_refused(self):
		"""The body the pen test read off 169.254.169.254."""
		metadata = '{"instance-id": "i-0123456789", "region": "ap-south-1"}'

		with self.assertRaises(frappe.ValidationError) as caught:
			validate_patch(metadata)

		self.assertIn("does not look like a patch", str(caught.exception))

	def test_html_error_page_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			validate_patch("<html><body><h1>404 Not Found</h1></body></html>")

	def test_empty_body_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			validate_patch("")

	def test_file_header_without_a_hunk_is_refused(self):
		"""Prose that happens to open with a diff-looking line is not a diff."""
		with self.assertRaises(frappe.ValidationError):
			validate_patch("diff --git a/README.md b/README.md\nnothing follows\n")

	def test_hunk_header_mentioned_in_prose_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			validate_patch("The patch starts at @@ -1,3 +1,4 @@ and goes on\n")
