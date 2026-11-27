import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.patches.v0_8_0.reapply_slave_connections_needed_for_purge import VARIABLE, execute
from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
	DatabaseServerMariaDBVariable,
)


@patch.object(DatabaseServerMariaDBVariable, "update_on_server")
class TestReapplySlaveConnectionsNeededForPurge(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def create_server_with_rollout(self, value) -> str:
		server = create_test_database_server()
		server.append("mariadb_system_variables", {"mariadb_variable": VARIABLE, "value_int": 0})
		server.save()
		frappe.get_doc(
			{
				"doctype": "Ansible Play",
				"server_type": "Database Server",
				"server": server.name,
				"playbook": "mysqld_variable.yml",
				"play": "Set mysqld variable",
				"status": "Failure" if value is None else "Success",
				"variables": json.dumps({"variable": VARIABLE, "value": value}),
			}
		).insert()
		return server.name

	def run_patch(self, live_value: str | None):
		rows = [] if live_value is None else [{"Variable_name": VARIABLE, "Value": live_value}]
		with patch.object(Agent, "fetch_database_variables", Mock(return_value=rows)):
			execute()

	def test_reapplies_variable_on_server_whose_rollout_sent_none(self, update_on_server):
		self.create_server_with_rollout(None)
		update_on_server.reset_mock()
		self.run_patch(live_value="1")
		update_on_server.assert_called_once()

	def test_skips_server_whose_rollout_sent_zero(self, update_on_server):
		self.create_server_with_rollout(0)
		update_on_server.reset_mock()
		self.run_patch(live_value="1")
		update_on_server.assert_not_called()

	def test_skips_mariadb_10_6_server_that_lacks_the_variable(self, update_on_server):
		self.create_server_with_rollout(None)
		update_on_server.reset_mock()
		self.run_patch(live_value=None)
		update_on_server.assert_not_called()
