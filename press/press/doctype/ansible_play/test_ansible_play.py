# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from frappe.types.DF import Data


def create_test_ansible_play(
	play: str = "",
	playbook: str = "",
	server_type: str = "Server",
	server: Data | None = "",
	vars: dict | None = None,
	status: str = "Success",
):
	if vars is None:
		vars = {}
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


class TestAnsiblePlay(FrappeTestCase):
	pass
