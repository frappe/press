# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from press.agent import Agent
from press.press.doctype.frappe_app.test_frappe_app import (
	create_test_frappe_app
)


def create_test_site(subdomain):
	"""Create test Site doc."""
	frappe.set_user("Administrator")

	proxy_server = frappe.get_doc({
		"doctype": "Proxy Server",
		"status": "Active",
		"ip": "0.0.0.0.0",
		"private_ip": "0.9.9.9.9",
		"name": "n.frappe.cloudtest",
	}).insert(ignore_if_duplicate=True)

	server = frappe.get_doc({
		"doctype": "Server",
		"status": "Active",
		"ip": "0.0.0.0",
		"private_ip": "9.9.9.9",
		"name": "f.frappe.cloudtest",
		"mariadb_root_password": "admin",
		"proxy_server": proxy_server.name
	}).insert(ignore_if_duplicate=True)

	frappe_app = create_test_frappe_app()

	release_group = frappe.get_doc({
		"doctype": "Release Group",
		"name": "Test Release Group",
		"apps": [{
			"app": frappe_app.name,
		}],
		"enabled": True
	}).insert(ignore_if_duplicate=True)

	release_group.create_deploy_candidate()

	bench = frappe.get_doc({
		"name": "Test Bench",
		"doctype": "Bench",
		"status": "Active",
		"workers": 1,
		"gunicorn_workers": 2,
		"group": release_group.name,
		"server": server.name
	}).insert(ignore_if_duplicate=True)

	plan = frappe.get_doc({
		"name": "Test 10 dollar plan",
		"doctype": "Plan",
		"price_inr": 750.0,
		"price_usd": 10.0,
		"period": 30
	}).insert(ignore_if_duplicate=True)

	return frappe.get_doc({
		"doctype": "Site",
		"status": "Active",
		"subdomain": subdomain,
		"server": server.name,
		"bench": bench.name,
		"plan": plan.name,
		"apps": [{
			"app": frappe_app.name
		}],
		"admin_password": "admin"
	}).insert(ignore_if_duplicate=True)


def fake_agent_job():
	"""Monkey patch Agent Job doctype methods to work in isolated tests."""

	def create_agent_job(
		self,
		job_type,
		path,
		data=None,
		files=None,
		method="POST",
		bench=None,
		site=None,
		upstream=None,
		host=None,
	):
		return {"job": 1}

	Agent.create_agent_job = create_agent_job


class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def setUp(self):
		self.subdomain = "testsubdomain"
		fake_agent_job()

	def tearDown(self):
		frappe.db.rollback()

	def test_primary_domain_is_default_when_no_site_domain_is_primary(self):
		site = create_test_site(self.subdomain)
