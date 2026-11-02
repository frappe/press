# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.blog import latest_blog, mark_read
from press.press.doctype.blog_read_status.blog_read_status import get_blog_read_status

BLOG = "https://frappe.io/blog/frappe-cloud/whats-new"
METADATA = {"title": "What's New", "description": "Our latest update"}


class TestBlogReadStatus(FrappeTestCase):
	def setUp(self):
		frappe.db.set_single_value("Press Settings", "latest_blog_url", BLOG)

	def tearDown(self):
		frappe.db.rollback()

	def test_get_blog_read_status_creates_one_record_per_user(self):
		first = get_blog_read_status(frappe.session.user)
		second = get_blog_read_status(frappe.session.user)

		self.assertEqual(first.name, second.name)
		self.assertEqual(first.user, frappe.session.user)

	def test_mark_read_records_the_blog_and_review_date(self):
		status = get_blog_read_status(frappe.session.user)
		status.mark_read(BLOG)

		self.assertEqual(status.last_read_blog, BLOG)
		self.assertEqual(status.last_reviewed_on, frappe.utils.today())
		self.assertTrue(status.has_read(BLOG))

	@patch("press.api.blog.get_blog_metadata", return_value=METADATA)
	def test_latest_blog_is_shown_until_it_is_read(self, _):
		self.assertTrue(latest_blog()["show"])

		mark_read(BLOG)
		self.assertFalse(latest_blog()["show"])

	@patch("press.api.blog.get_blog_metadata", return_value=METADATA)
	def test_reviewing_does_not_hide_an_unread_blog(self, _):
		get_blog_read_status(frappe.session.user).mark_reviewed()

		self.assertTrue(latest_blog()["show"])

	def test_latest_blog_is_hidden_when_no_url_is_set(self):
		frappe.db.set_single_value("Press Settings", "latest_blog_url", "")

		self.assertFalse(latest_blog()["show"])
