# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from press.agent import Agent

from .bench import Bench


def create_test_bench(release_group: str, server: str) -> Bench:
	"""
	Create test Bench doc.

	API call to agent will be faked when creating the doc.
	"""
	fake_agent_job()
	name = frappe.mock("name")
	return frappe.get_doc(
		{
			"name": f"Test Bench{name}",
			"doctype": "Bench",
			"status": "Active",
			"workers": 1,
			"gunicorn_workers": 2,
			"group": release_group,
			"server": server,
		}
	).insert(ignore_if_duplicate=True)


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


class TestBench(unittest.TestCase):
	pass
