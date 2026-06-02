# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for user_ssh_certificate/user_ssh_certificate.py.

validate() checks for a valid public key.
before_save() computes an SHA-256 fingerprint of the public key.
_set_key_type() extracts the key type from the public key header.
All are tested without DB round-trips using SimpleNamespace docs.
"""

from __future__ import annotations

import base64
import hashlib
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.user_ssh_certificate.user_ssh_certificate import UserSSHCertificate

_MODULE = "press.press.doctype.user_ssh_certificate.user_ssh_certificate"

# A synthetic ED25519 key whose base64 body is exactly 44 chars (32 zero bytes).
# 44 chars is a valid base64 string (44 mod 4 == 0, no padding needed).
_VALID_KEY = "ssh-ed25519 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= test@example"
_INVALID_KEY = "ssh-rsa NotValidBase64!!!! test@example"


def _doc(**kwargs):
	defaults = dict(
		user="user@example.com",
		ssh_public_key=_VALID_KEY,
		access_server="",
		all_servers=0,
		ssh_fingerprint=None,
		key_type=None,
	)
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# UserSSHCertificate.validate
# ══════════════════════════════════════════════════════════════════════════════


class TestUserSSHCertificateValidate(FrappeTestCase):
	"""validate() raises for missing or invalid public keys."""

	def test_raises_when_public_key_is_missing(self):
		doc = _doc(ssh_public_key=None)
		with self.assertRaises(frappe.ValidationError):
			UserSSHCertificate.validate(doc)

	def test_raises_when_public_key_is_empty_string(self):
		doc = _doc(ssh_public_key="")
		with self.assertRaises(frappe.ValidationError):
			UserSSHCertificate.validate(doc)

	def test_raises_for_invalid_base64_key(self):
		doc = _doc(ssh_public_key=_INVALID_KEY)
		with self.assertRaises(frappe.ValidationError):
			UserSSHCertificate.validate(doc)

	def test_passes_for_valid_ed25519_key(self):
		doc = _doc(ssh_public_key=_VALID_KEY)
		UserSSHCertificate.validate(doc)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# UserSSHCertificate.before_save — fingerprint computation
# ══════════════════════════════════════════════════════════════════════════════


class TestUserSSHCertificateBeforeSave(FrappeTestCase):
	"""before_save() computes and stores the SSH fingerprint."""

	def test_fingerprint_set_after_before_save(self):
		doc = _doc(ssh_public_key=_VALID_KEY)
		UserSSHCertificate.before_save(doc)
		self.assertIsNotNone(doc.ssh_fingerprint)
		self.assertGreater(len(doc.ssh_fingerprint), 0)

	def test_fingerprint_is_base64_encoded_sha256(self):
		"""The fingerprint should be the base64 of the SHA-256 of the decoded key."""
		doc = _doc(ssh_public_key=_VALID_KEY)
		UserSSHCertificate.before_save(doc)

		key_b64 = _VALID_KEY.strip().split()[1]
		raw = base64.b64decode(key_b64)
		sha = hashlib.sha256(raw).digest()
		expected = base64.b64encode(sha).decode()
		self.assertEqual(doc.ssh_fingerprint, expected)

	def test_fingerprint_is_deterministic(self):
		"""Same public key always produces the same fingerprint."""
		doc1 = _doc(ssh_public_key=_VALID_KEY)
		doc2 = _doc(ssh_public_key=_VALID_KEY)
		UserSSHCertificate.before_save(doc1)
		UserSSHCertificate.before_save(doc2)
		self.assertEqual(doc1.ssh_fingerprint, doc2.ssh_fingerprint)


# ══════════════════════════════════════════════════════════════════════════════
# UserSSHCertificate._set_key_type
# ══════════════════════════════════════════════════════════════════════════════


class TestUserSSHCertificateSetKeyType(FrappeTestCase):
	"""_set_key_type() extracts the key algorithm from the public key prefix."""

	def test_ed25519_key_type(self):
		doc = _doc(ssh_public_key="ssh-ed25519 AAAAC3Nza test@example")
		UserSSHCertificate._set_key_type(doc)
		self.assertEqual(doc.key_type, "ed25519")

	def test_rsa_key_type(self):
		doc = _doc(ssh_public_key="ssh-rsa AAAAB3Nza test@example")
		UserSSHCertificate._set_key_type(doc)
		self.assertEqual(doc.key_type, "rsa")

	def test_ecdsa_key_type(self):
		doc = _doc(ssh_public_key="ecdsa-sha2-nistp256 AAAA test@example")
		UserSSHCertificate._set_key_type(doc)
		self.assertEqual(doc.key_type, "sha2")
