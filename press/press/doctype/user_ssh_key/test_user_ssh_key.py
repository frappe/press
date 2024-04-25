# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import cryptography
import frappe
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_press_admin_team


def create_rsa_key() -> str:
	key = rsa.generate_private_key(
		public_exponent=65537,
		key_size=2048,
		backend=cryptography.hazmat.backends.default_backend(),
	)
	str_key = (
		key.public_key().public_bytes(
			encoding=cryptography.hazmat.primitives.serialization.Encoding.OpenSSH,
			format=cryptography.hazmat.primitives.serialization.PublicFormat.OpenSSH,
		),
	)
	return str_key[0].decode("utf-8")


def create_ed25519_key() -> str:
	key = Ed25519PrivateKey.generate()
	str_key = (
		key.public_key().public_bytes(
			encoding=cryptography.hazmat.primitives.serialization.Encoding.OpenSSH,
			format=cryptography.hazmat.primitives.serialization.PublicFormat.OpenSSH,
		),
	)
	return str_key[0].decode("utf-8")


def create_test_user_ssh_key(user: str, str_key: str = None):
	"""Create a test SSH key for the given user."""
	if not str_key:
		str_key = create_rsa_key()
	ssh_key = frappe.get_doc(
		{
			"doctype": "User SSH Key",
			"user": user,
			"ssh_public_key": str_key,
		}
	).insert(ignore_if_duplicate=True)
	ssh_key.reload()
	return ssh_key


class TestUserSSHKey(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_valid_ssh_key_works_with_rsa_key(self):
		team = create_test_press_admin_team()
		user = frappe.get_doc("User", team.user)
		try:
			create_test_user_ssh_key(user.name)
		except Exception:
			self.fail("Adding a valid RSA SSH key failed")

	def test_create_valid_ssh_key_works_with_ed25519(self):
		"""Test that creating a valid SSH key works."""
		team = create_test_press_admin_team()
		user = frappe.get_doc("User", team.user)
		try:
			create_test_user_ssh_key(user.name, create_ed25519_key())
		except Exception:
			self.fail("Adding a valid Ed25519 SSH key failed")

	def test_adding_certificate_as_key_fails(self):
		"""Test that creating an invalid SSH key fails."""
		team = create_test_press_admin_team()
		user = frappe.get_doc("User", team.user)
		with self.assertRaisesRegex(frappe.ValidationError, "Key type has to be one of.*"):
			create_test_user_ssh_key(user.name, "ssh-ed25519-cert-v01@openssh.com FAKE_KEY")

	def test_adding_single_word_fails(self):
		team = create_test_press_admin_team()
		user = frappe.get_doc("User", team.user)
		with self.assertRaisesRegex(
			frappe.ValidationError, "You must supply a key in OpenSSH public key format"
		):
			create_test_user_ssh_key(user.name, "ubuntu@frappe.cloud")

	def test_adding_partial_of_valid_key_with_valid_number_of_data_characters_fails(
		self,
	):
		team = create_test_press_admin_team()
		user = frappe.get_doc("User", team.user)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"copy/pasting the key using one of the commands in documentation",
		):
			create_test_user_ssh_key(
				user.name,
				"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDB3zVjTzHQSEHQG7OD3bYi7V1xk+PCwko0W3+d1fSUvSDCxSMKtR31+CfMKmjnvoHubOHYI9wvLpx6KdZUl2uO",
			)
