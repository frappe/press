from __future__ import annotations

# Copyright (c) 2021, Frappe and Contributors
# See license.txt
import unittest
from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from press.press.doctype.ssh_key.ssh_key import SSHKey


def create_test_ssh_key() -> SSHKey:
	return frappe.get_doc(
		{
			"doctype": "SSH Key",
			"name": "Test SSH Key",
			"public_key": "ssh-rsa AAAAB3",
		}
	).insert(ignore_if_duplicate=True)


class TestSSHKey(unittest.TestCase):
	pass
