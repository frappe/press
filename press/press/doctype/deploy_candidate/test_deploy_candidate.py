# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from press.press.doctype.release_group.release_group import ReleaseGroup

import unittest

import frappe


def create_test_deploy_candidate(group: ReleaseGroup):
	"""
	Create Test Deploy Candidate doc
	"""
	deploy_candidate = frappe.get_doc(
		{
			"doctype": "Deploy Candidate",
			"team": group.team,
			"group": group.name,
			"apps": group.apps,
			"dependencies": group.dependencies,
		}
	)
	deploy_candidate.insert()
	return deploy_candidate


class TestDeployCandidate(unittest.TestCase):
	pass
