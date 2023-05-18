# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.ssh_certificate.ssh_certificate import SSHCertificate
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.user_ssh_key.test_user_ssh_key import create_test_user_ssh_key


@patch.object(SSHCertificate, "validate_certificate_authority", new=Mock())
@patch.object(SSHCertificate, "generate_certificate", new=Mock())
@patch.object(SSHCertificate, "extract_certificate_details", new=Mock())
@patch.object(SSHCertificate, "extract_certificate_details", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSSHCertificate(unittest.TestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.user = self.team.user

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_press_admin_user_can_create_ssh_certificate(self):
		bench = create_test_bench(self.user)
		group = bench.group
		frappe.set_user(self.user)
		user_ssh_key = create_test_user_ssh_key(user=self.user)
		return frappe.get_doc(
			{
				"doctype": "SSH Certificate",
				"certificate_type": "User",
				"group": group,
				"user": frappe.session.user,
				"user_ssh_key": user_ssh_key,
				"validity": "6h",
			}
		).insert()
