# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.press_settings.press_settings import PressSettings


def create_test_press_settings():
	"""Create test press settings doc"""
	settings = frappe.get_doc(
		{
			"doctype": "Press Settings",
			"domain": "fc.dev",
			"bench_configuration": "JSON",
			"dns_provider": "AWS Route 53",
			"rsa_key_size": "2048",
		}
	).insert()
	return settings


class TestPressSettings(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch.object(PressSettings, "_set_lifecycle_config")
	def test_lifecycle_config_is_called_on_create(self, mock_set_lifecycle_config):
		create_test_press_settings()
		mock_set_lifecycle_config.assert_called_once()

	@patch.object(PressSettings, "_set_lifecycle_config")
	def test_lifecycle_config_is_updated_on_settings_update(
		self, mock_set_lifecycle_config
	):
		press_settings = create_test_press_settings()
		mock_set_lifecycle_config.reset_mock()
		press_settings.offsite_backups_lifecycle_config = "{}"
		press_settings.save()
		mock_set_lifecycle_config.assert_called_once()

	@patch.object(PressSettings, "_set_lifecycle_config")
	def test_lifecycle_config_not_updated_when_unreleated_field_updated(
		self, mock_set_lifecycle_config
	):
		press_settings = create_test_press_settings()
		mock_set_lifecycle_config.reset_mock()
		press_settings.aws_s3_bucket = "fake-bucket-name"
		press_settings.save()
		mock_set_lifecycle_config.assert_not_called()

	@patch.object(PressSettings, "boto3_session")
	def test_log_is_created_for_lifecycle_update(self, mock_boto3_session):
		log_count_before = frappe.db.count("Remote Operation Log")
		press_settings = create_test_press_settings()
		press_settings.offsite_backups_lifecycle_config = "{}"
		press_settings.save()
		log_count_after = frappe.db.count("Remote Operation Log")
		self.assertGreater(
			log_count_after, log_count_before, msg=(log_count_after, log_count_before)
		)
