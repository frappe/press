# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_ansible_play_task(
	play: str = "",
	role: str = "",
	task: str = "",
	status: str = "Success",
	output: str = "",
):
	play = frappe.get_doc(
		{
			"doctype": "Ansible Task",
			"play": play,
			"role": role,
			"task": task,
			"status": status,
			"output": output,
		}
	).insert()
	# play.db_set("status", status)
	play.reload()
	return play


class TestAnsibleTask(unittest.TestCase):
	pass
