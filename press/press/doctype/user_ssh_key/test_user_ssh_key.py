# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import unittest

import cryptography
import frappe
from cryptography.hazmat.primitives.asymmetric import rsa


def create_test_user_ssh_key(user: str):
	"""Create a test SSH key for the given user."""
	key = rsa.generate_private_key(
		public_exponent=65537,
		key_size=2048,
		backend=cryptography.hazmat.backends.default_backend(),
	)
	return frappe.get_doc(
		{
			"doctype": "User SSH Key",
			"user": user,
			"ssh_public_key": key.public_key().public_bytes(
				encoding=cryptography.hazmat.primitives.serialization.Encoding.OpenSSH,
				format=cryptography.hazmat.primitives.serialization.PublicFormat.OpenSSH,
			),
		}
	).insert(ignore_if_duplicate=True)


class TestUserSSHKey(unittest.TestCase):
	pass
