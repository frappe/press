# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_ansible_play(
	play: str = "",
	playbook: str = "",
	server_type: str = "Server",
	server: str = "",
	vars: dict = {},
):
	play = frappe.get_doc(
		{
			"doctype": "Ansible Play",
			"status": "Success",
			"play": play,
			"playbook": playbook,
			"server_type": server_type,
			"server": server,
			"variable": vars,
		}
	).insert()
	play.db_set("status", "Success")
	play.reload()
	return play


class TestAnsiblePlay(unittest.TestCase):
	pass
