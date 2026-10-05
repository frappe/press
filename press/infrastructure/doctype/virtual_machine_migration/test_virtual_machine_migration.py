# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.infrastructure.doctype.virtual_machine_migration.virtual_machine_migration import (
	StepStatus,
	VirtualMachineMigration,
)


class TestVirtualMachineMigration(FrappeTestCase):
	def _run_bind_mount_permissions(self, bind_mounts):
		migration = frappe.get_doc({"doctype": "Virtual Machine Migration", "bind_mounts": bind_mounts})
		with patch.object(
			VirtualMachineMigration, "ansible_run", return_value={"status": "Success"}
		) as ansible_run:
			status = migration.update_bind_mount_permissions()
		self.assertEqual(status, StepStatus.Success)
		return [call.args[0] for call in ansible_run.call_args_list]

	def test_docker_data_dir_is_not_chowned_recursively(self):
		commands = self._run_bind_mount_permissions(
			[
				{
					"source_mount_point": "/opt/volumes/benches/var/lib/docker",
					"service": "docker",
					"mount_point_owner": "root",
					"mount_point_group": "root",
				}
			]
		)
		self.assertIn("chown root:root /opt/volumes/benches/var/lib/docker", commands)
		self.assertFalse(any("chown -R" in command for command in commands))

	def test_other_bind_mounts_are_chowned_recursively(self):
		commands = self._run_bind_mount_permissions(
			[
				{
					"source_mount_point": "/opt/volumes/benches/home/frappe/benches",
					"service": "docker",
					"mount_point_owner": "frappe",
					"mount_point_group": "frappe",
				},
				{
					"source_mount_point": "/opt/volumes/mariadb/var/lib/mysql",
					"service": "mariadb",
					"mount_point_owner": "mysql",
					"mount_point_group": "mysql",
				},
			]
		)
		self.assertIn("chown -R frappe:frappe /opt/volumes/benches/home/frappe/benches", commands)
		self.assertIn("chown -R mysql:mysql /opt/volumes/mariadb/var/lib/mysql", commands)

	def test_steps_run_on_long_queue_with_extended_timeout(self):
		migration = frappe.get_doc(
			{
				"doctype": "Virtual Machine Migration",
				"steps": [
					{
						"step": "Update bind mount permissions",
						"method": "update_bind_mount_permissions",
						"status": "Pending",
					}
				],
			}
		)
		with (
			patch.object(VirtualMachineMigration, "save"),
			patch("frappe.enqueue_doc") as enqueue_doc,
		):
			migration.next()
		kwargs = enqueue_doc.call_args.kwargs
		self.assertEqual(kwargs["queue"], "long")
		self.assertGreater(kwargs["timeout"], 300)
