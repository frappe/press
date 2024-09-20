# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import unittest

import frappe


def create_test_ansible_play(
	play: str = "",
	playbook: str = "",
	server_type: str = "Server",
	server: str = "",
	vars: dict | None = None,
	status: str = "Success",
):
	vars = {} if vars is None else vars
	play = frappe.get_doc(
		{
			"doctype": "Ansible Play",
			"play": play,
			"playbook": playbook,
			"server_type": server_type,
			"server": server,
			"variable": vars,
		}
	).insert()
	play.db_set("status", status)
	play.reload()
	return play


class TestAnsiblePlay(unittest.TestCase):
	pass
