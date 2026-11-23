import frappe
from ansible.playbook import Playbook
from ansible.playbook.play_context import PlayContext
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.server.test_server import create_test_server
from press.runner import ANSIBLE_CONNECTION_TIMEOUT, Ansible


class TestAnsibleConnectionTimeout(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_ansible_play_context_uses_connection_timeout_instead_of_zero(self):
		ansible = Ansible(server=create_test_server(), playbook="ping.yml")
		playbook = Playbook.load(
			ansible.playbook_path, variable_manager=ansible.variable_manager, loader=ansible.loader
		)

		play_context = PlayContext(playbook.get_plays()[0])

		self.assertEqual(play_context.timeout, ANSIBLE_CONNECTION_TIMEOUT)
