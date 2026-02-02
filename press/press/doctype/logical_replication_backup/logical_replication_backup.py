# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json
import time
from enum import Enum
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.logical_replication_step.logical_replication_step import LogicalReplicationStep
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.server.server import BaseServer, Server
	from press.press.doctype.server_snapshot.server_snapshot import ServerSnapshot
	from press.press.doctype.site.site import Site


StepStatus = Enum("StepStatus", ["Pending", "Running", "Skipped", "Success", "Failure"])

VOLUME_INITIALIZATION_RATE = 300  # in MB/s, this is the rate at which the volume will be initialized
MINIMUM_REPLICATION_LAG_FOR_TAKING_DOWNTIME = (
	1200  # in seconds, this is the minimum replication lag required before taking downtime
)

"""
Replication configuration keys
- read_from_replica: bool
- allow_reads_during_maintenance: bool
- replica_host: str
"""
REPLICATION_CONFIG_KEYS = [
	"read_from_replica",
	"allow_reads_during_maintenance",
	"replica_host",
]


def check_replication_lag(server: "DatabaseServer", target_lag: int) -> int:
	# -1 -> Something wrong with replication, consider as failure
	# 0 -> We haven't yet reached the targetted replication lag
	# 1 -> We have reached the targetted replication lag
	try:
		data = server.get_replication_status()
		if not data.get("success", False):
			# If the replication status is not available
			# Might be agent or db is not in a state to fetch the replication status
			# Just keep trying
			return 0
		replication_status = data.get("data", {}).get("slave_status", {})
		if not replication_status:
			# No replication status available
			# That means server is not replicating even
			# Means failed replication setup
			return -1

		if (
			# No replication status available
			# That means server is not replicating even
			# Means failed replication setup
			not replication_status
			# Usually `Seconds_Behind_Master` should be there
			# If not there, then replication is not running and fail it
			or "Seconds_Behind_Master" not in replication_status
			# If any error in replication
			# Mark the process as failure
			# As it's not safe to proceed + not easy to automatically fix
			or replication_status.get("Last_Errno", 0) != 0
			or replication_status.get("Last_IO_Errno", 0) != 0
			or replication_status.get("Last_SQL_Errno", 0) != 0
			or replication_status.get("Slave_IO_Running") != "Yes"
			or replication_status.get("Slave_SQL_Running") != "Yes"
		):
			"""
			During doing multiple stuffs like setting up different configurations and all
			Replication can take some time to start

			So, Ignore the network issues or connection issues
			"""
			if replication_status and (
				replication_status.get("Last_IO_Errno") == 2003
				or "error reconnecting to master" in replication_status.get("Last_SQL_Errno", "")
			):
				return 0

			# Replication is not running
			return -1

		if (
			replication_status.get("Seconds_Behind_Master", 10000000000)  # Default to a large number
			<= target_lag
		):
			# Replication lag is less than the minimum required
			return 1

		return 0

	except Exception:
		return 0


class LogicalReplicationBackup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.logical_replication_server.logical_replication_server import (
			LogicalReplicationServer,
		)
		from press.press.doctype.logical_replication_step.logical_replication_step import (
			LogicalReplicationStep,
		)

		bench_replication_config: DF.SmallText | None
		database_server: DF.Link
		duration: DF.Duration | None
		end: DF.Datetime | None
		execution_stage: DF.Literal["Pre-Migrate", "Post-Migrate", "Failover"]
		failover_stage_status: DF.Literal["Pending", "Running", "Success", "Failure"]
		failover_steps: DF.Table[LogicalReplicationStep]
		initial_binlog_position_of_new_primary_db: DF.Data | None
		post_migrate_stage_status: DF.Literal["Pending", "Running", "Success", "Failure"]
		post_migrate_steps: DF.Table[LogicalReplicationStep]
		pre_migrate_stage_status: DF.Literal["Pending", "Running", "Success", "Failure"]
		pre_migrate_steps: DF.Table[LogicalReplicationStep]
		server: DF.Link
		server_snapshot: DF.Link | None
		servers: DF.Table[LogicalReplicationServer]
		site: DF.Link
		site_replication_config: DF.SmallText | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		# end: auto-generated types

		SyncStep = False
		AsyncStep = True
		Wait = True
		NoWait = False

	def get_steps__template(self, context: Literal["pre_migrate", "post_migrate", "failover"]):
		SyncStep = False
		AsyncStep = True  # some external job
		Wait = True
		NoWait = False
		PreMigrateStep = "pre_migrate"
		PostMigrateStep = "post_migrate"
		FailoverStep = "failover"

		methods = [
			(self.pre__validate_existing_replica_health, SyncStep, NoWait, PreMigrateStep),
			(self.pre__create_consistent_server_snapshot, SyncStep, NoWait, PreMigrateStep),
			(self.pre__wait_for_servers_to_be_online, SyncStep, Wait, PreMigrateStep),
			(self.pre__wait_for_server_snapshot_to_be_ready, AsyncStep, NoWait, PreMigrateStep),
			(self.pre__lock_server_snapshot, SyncStep, NoWait, PreMigrateStep),
			(self.pre__provision_hot_standby_database_server, SyncStep, Wait, PreMigrateStep),
			(self.pre__wait_for_hot_standby_volume_initialization, SyncStep, Wait, PreMigrateStep),
			(self.pre__wait_for_hot_standby_database_server_to_be_ready, AsyncStep, NoWait, PreMigrateStep),
			(self.pre__wait_for_minimal_replication_lag, SyncStep, Wait, PreMigrateStep),
			(self.pre__enable_maintenance_mode_in_site, AsyncStep, NoWait, PreMigrateStep),
			(self.pre__enable_read_only_mode_in_database_server, AsyncStep, NoWait, PreMigrateStep),
			(self.pre__wait_for_database_server_to_be_available, SyncStep, Wait, PreMigrateStep),
			(self.pre__remove_replication_configuration_from_site, SyncStep, NoWait, PreMigrateStep),
			(self.pre__wait_for_complete_hot_standby_replica_syncing, SyncStep, Wait, PreMigrateStep),
			(self.pre__wait_for_complete_other_replica_syncing, SyncStep, Wait, PreMigrateStep),
			(self.pre__stop_hot_standby_database_replication, SyncStep, NoWait, PreMigrateStep),
			(self.pre__stop_other_replica_database_replication, SyncStep, NoWait, PreMigrateStep),
			(self.pre__disable_read_only_mode_from_database_server, SyncStep, NoWait, PreMigrateStep),
			(self.pre__wait_for_database_server_to_be_available, SyncStep, Wait, PreMigrateStep),
			####################################################################################
			(self.post__archive_hot_standby_database_server, SyncStep, NoWait, PostMigrateStep),
			(self.post__activate_sites, AsyncStep, NoWait, PostMigrateStep),
			(self.post__enable_replication_on_replica, SyncStep, NoWait, PostMigrateStep),
			(self.post__wait_for_minimal_replication_lag_of_replica, SyncStep, Wait, PostMigrateStep),
			(
				self.post__restore_replication_configuration_of_site_and_bench,
				AsyncStep,
				NoWait,
				PostMigrateStep,
			),
			####################################################################################
			(self.failover__plan_and_assign_new_role_to_servers, SyncStep, NoWait, FailoverStep),
			(
				self.failover__configure_hot_standby_database_server_as_new_master,
				SyncStep,
				NoWait,
				FailoverStep,
			),
			(self.failover__update_reference_to_new_master_database_server, SyncStep, NoWait, FailoverStep),
			(self.failover__update_new_master_database_server_plan_and_team, SyncStep, NoWait, FailoverStep),
			(self.failover__gather_binlog_position_from_new_master, SyncStep, Wait, FailoverStep),
			(self.failover__update_master_database_ref_in_replica_servers, SyncStep, NoWait, FailoverStep),
			(self.failover__disable_read_only_mode_on_new_master, SyncStep, NoWait, FailoverStep),
			(self.failover__wait_for_master_database_server_to_be_available, SyncStep, Wait, FailoverStep),
			(self.failover__configure_sites_with_new_master_database_server, AsyncStep, NoWait, FailoverStep),
			(self.failover__activate_sites, AsyncStep, NoWait, FailoverStep),
			(self.failover__join_other_replicas_to_new_master, SyncStep, NoWait, FailoverStep),
			(self.failover__start_replication_on_replica, SyncStep, NoWait, FailoverStep),
			(self.failover__wait_for_minimal_replication_lag_of_replica, SyncStep, Wait, FailoverStep),
			(
				self.failover__restore_replication_configuration_of_site_and_bench,
				AsyncStep,
				NoWait,
				FailoverStep,
			),
			(self.failover__archive_old_primary_database_server, SyncStep, NoWait, FailoverStep),
			(self.failover__create_subscription_for_new_master, SyncStep, NoWait, FailoverStep),
		]

		steps = []
		for (
			method,
			is_async,
			wait_for_completion,
			step_context,
		) in methods:
			if step_context != context:
				continue
			steps.append(
				{
					"step": method.__doc__,
					"method": method.__name__,
					"is_async": is_async,
					"wait_for_completion": wait_for_completion,
				}
			)
		return steps

	@property
	def pre_migrate_steps__template(self):
		return self.get_steps__template("pre_migrate")

	@property
	def post_migrate_steps__template(self):
		return self.get_steps__template("post_migrate")

	@property
	def failover_steps__template(self):
		return self.get_steps__template("failover")

	@property
	def stage_status(self):
		if self.execution_stage == "Pre-Migrate":
			return self.pre_migrate_stage_status
		if self.execution_stage == "Post-Migrate":
			return self.post_migrate_stage_status
		if self.execution_stage == "Failover":
			return self.failover_stage_status
		frappe.throw("Invalid execution stage for getting stage status")
		return None

	@stage_status.setter
	def stage_status(self, value: Literal["Pending", "Running", "Success", "Failure"]):
		if self.execution_stage == "Pre-Migrate":
			self.pre_migrate_stage_status = value
		elif self.execution_stage == "Post-Migrate":
			self.post_migrate_stage_status = value
		elif self.execution_stage == "Failover":
			self.failover_stage_status = value
		else:
			frappe.throw("Invalid execution stage for setting stage status.")

	@property
	def site_doc(self) -> "Site":
		return frappe.get_doc("Site", self.site)

	@property
	def release_group_doc(self) -> "ReleaseGroup":
		return frappe.get_doc("Release Group", frappe.db.get_value("Site", self.site, "group"))

	@property
	def server_snapshot_doc(self) -> "ServerSnapshot":
		return frappe.get_doc("Server Snapshot", self.server_snapshot)

	@property
	def app_server_doc(self) -> "Server":
		return frappe.get_doc("Server", self.server)

	@property
	def database_server_doc(self) -> "DatabaseServer":
		return frappe.get_doc("Database Server", self.database_server)

	@property
	def replica_database_servers(self) -> list[str]:
		return [s.database_server for s in self.servers if s.current_role == "Replica"]

	@property
	def new_replica_database_servers(self) -> list[str]:
		return [s.database_server for s in self.servers if s.new_role == "Replica"]

	@property
	def replica_database_server_docs(self) -> list["DatabaseServer"]:
		replica_servers = []
		for s in self.servers:
			if s.current_role == "Replica":
				replica_servers.append(frappe.get_doc("Database Server", s.database_server))
		return replica_servers

	@property
	def new_replica_database_server_docs(self) -> list["DatabaseServer"]:
		new_replica_servers = []
		for s in self.servers:
			if s.new_role == "Replica":
				new_replica_servers.append(frappe.get_doc("Database Server", s.database_server))
		return new_replica_servers

	@property
	def hot_standby_database_server(self) -> "str | None":
		server = None
		for s in self.servers:
			if s.current_role == "Hot Standby":
				server = s.database_server

		return server

	@property
	def hot_standby_database_server_doc(self) -> "DatabaseServer | None":
		hot_standby_server = self.hot_standby_database_server
		if not hot_standby_server:
			return None
		return frappe.get_doc("Database Server", hot_standby_server)

	@property
	def site_replication_config_dict(self) -> dict:  # type: ignore[return-value]
		try:
			return json.loads(self.site_replication_config or "{}")
		except json.JSONDecodeError:
			frappe.throw("Invalid site replication config JSON format.")

	@property
	def bench_replication_config_dict(self) -> dict:  # type: ignore[return-value]
		try:
			return json.loads(self.bench_replication_config or "{}")
		except json.JSONDecodeError:
			frappe.throw("Invalid bench replication config JSON format.")

	def after_insert(self):
		self.populate_server_infos()
		self.add_steps()
		self.store_db_replication_config_of_site(save=False)
		self.store_replication_config_of_bench(save=False)
		self.save()

	def on_update(self):
		stage_status_updated = (
			self.has_value_changed("pre_migrate_stage_status")
			or self.has_value_changed("post_migrate_stage_status")
			or self.has_value_changed("failover_stage_status")
		)
		if self.has_value_changed("execution_stage") or stage_status_updated:
			new_status = self.status
			if self.execution_stage == "Pre-Migrate":
				new_status = {
					"Pending": "Pending",
					"Running": "Running",
					"Success": "Running",  # Because some other stage need to run for overall status
					"Failure": "Failure",
				}[self.pre_migrate_stage_status]
			elif self.execution_stage == "Post-Migrate":
				new_status = {
					"Pending": "Pending",
					"Running": "Running",
					"Success": "Success",
					"Failure": "Failure",
				}[self.post_migrate_stage_status]
			elif self.execution_stage == "Failover":
				new_status = {
					"Pending": "Pending",
					"Running": "Running",
					"Success": "Success",
					"Failure": "Failure",
				}[self.failover_stage_status]

			if self.status != new_status:
				self.status = new_status
				self.save()

		if stage_status_updated:
			self.callback_to_linked_site_update()

	#########################################################
	#                Pre Migrate Steps                      #
	#########################################################
	def pre__validate_existing_replica_health(self):
		"""Validate Existing Replica Health"""
		return StepStatus.Success

	def pre__create_consistent_server_snapshot(self):
		"""Create Consistent Snapshot Of Servers"""
		try:
			self.server_snapshot = self.app_server_doc._create_snapshot(consistent=True)
			self.save()
			return StepStatus.Success
		except Exception as e:
			frappe.throw(f"Failed to create consistent server snapshot: {e}")
			return StepStatus.Failure

	def pre__wait_for_servers_to_be_online(self):
		"""Wait For Servers To Be Online"""

		servers = [["Server", self.server], ["Database Server", self.database_server]]
		for doctype, name in servers:
			server: "BaseServer" = frappe.get_doc(doctype, name)
			if server.status != "Active":
				time.sleep(1)
				return StepStatus.Running

			server.ping_ansible()

			plays = frappe.get_all(
				"Ansible Play",
				{"server": name, "play": "Ping Server"},
				["status"],
				order_by="creation desc",
				limit=1,
			)

			if not plays or plays[0].status in ["Pending", "Running", "Failure"]:
				return StepStatus.Running

		return StepStatus.Success

	def pre__wait_for_server_snapshot_to_be_ready(self):
		"""Wait For Snapshot To Be Ready"""
		status = frappe.get_value(
			"Server Snapshot",
			self.server_snapshot,
			"status",
		)
		if status in ["Pending", "Processing"]:
			return StepStatus.Running
		if status == "Completed":
			return StepStatus.Success
		return StepStatus.Failure

	def pre__lock_server_snapshot(self):
		"""Lock Server Snapshot"""
		self.server_snapshot_doc.lock()
		return StepStatus.Success

	def pre__provision_hot_standby_database_server(self):
		"""Provision Hot Standby Database Server"""
		hot_standby_database_server: "DatabaseServer" = self.server_snapshot_doc.create_server(
			server_type="Database Server",
			provision_db_replica=True,
			create_subscription=False,  # Don't charge hot standby database server
			master_db_server=self.database_server,
			title=self.database_server_doc.title + " (Hot Standby)",
			team=self.database_server_doc.team,
			plan=self.database_server_doc.plan,
			press_job_arguments={
				"logical_replication_backup": self.name,
			},
		)
		self.append(
			"servers",
			{"current_role": "Hot Standby", "database_server": hot_standby_database_server, "new_role": ""},
		)
		self.save()
		return StepStatus.Success

	def pre__wait_for_hot_standby_volume_initialization(self):
		"""Wait For Hot Standby Volume Initialization"""
		# Can be optimized not to spawn up a bg job to just wait
		db_server_snapshot_size = frappe.get_value(
			"Virtual Disk Snapshot",
			frappe.get_value("Server Snapshot", self.server_snapshot, "app_server_snapshot"),
			"size",
		)
		required_initialization_time = db_server_snapshot_size * 1024 / VOLUME_INITIALIZATION_RATE
		server_creation_time = frappe.get_value(
			"Database Server",
			self.hot_standby_database_server,
			"creation",
		)
		if (frappe.utils.now_datetime() - server_creation_time).seconds > required_initialization_time:
			return StepStatus.Success
		return StepStatus.Running

	def pre__wait_for_hot_standby_database_server_to_be_ready(self):
		"""Wait For Hot Standby Database Server To Be Ready"""
		server = self.hot_standby_database_server_doc
		if server.status != "Active":
			return StepStatus.Running

		# Check status of Create Server Press Job
		press_job_status = frappe.db.get_value(
			"Press Job",
			{"server_type": "Database Server", "server": server.name, "job_type": "Create Server"},
			"status",
		)
		if not press_job_status:
			# Press Job might not have created yet
			return StepStatus.Running

		if press_job_status in ["Pending", "Running"]:
			return StepStatus.Running

		if press_job_status == "Failure":
			return StepStatus.Failure

		# Check if replication setup done
		if not server.is_replication_setup:
			return StepStatus.Running

		return StepStatus.Success

	def pre__wait_for_minimal_replication_lag(self):
		"""Wait For Minimal Replication Lag"""
		lag_status = check_replication_lag(
			self.hot_standby_database_server_doc, MINIMUM_REPLICATION_LAG_FOR_TAKING_DOWNTIME
		)
		if lag_status == -1:
			return StepStatus.Failure
		return StepStatus.Success if lag_status == 1 else StepStatus.Running

	def pre__enable_maintenance_mode_in_site(self):
		"""Enable Maintenance Mode For All Sites"""
		status = self.deactivate_site()
		if status == "Success":
			return StepStatus.Success
		if status == "Failure":
			return StepStatus.Failure
		return StepStatus.Running

	def pre__enable_read_only_mode_in_database_server(self):
		"""Enable Read Only Mode In Database Server"""
		self.database_server_doc.enable_read_only_mode(update_variables_synchronously=True)
		return StepStatus.Success

	def pre__wait_for_database_server_to_be_available(self):
		"""Wait For Database Server To Be Online"""
		if self.database_server_doc.ping_mariadb():
			return StepStatus.Success

		return StepStatus.Running

	def pre__remove_replication_configuration_from_site(self):
		"""Remove Replication Configuration From Site"""
		self.remove_replication_config_from_site_and_bench()
		return StepStatus.Success

	def pre__wait_for_complete_hot_standby_replica_syncing(self):
		"""Wait For Complete Hot Standby Replica Syncing"""

		lag_status = check_replication_lag(self.hot_standby_database_server_doc, 0)
		if lag_status == -1:
			return StepStatus.Failure
		return StepStatus.Success if lag_status == 1 else StepStatus.Running

	def pre__wait_for_complete_other_replica_syncing(self):
		"""Wait For Complete Other Replica Syncing"""

		for replica in self.replica_database_server_docs:
			lag_status = check_replication_lag(replica, 0)
			if lag_status == -1:
				return StepStatus.Failure
			if lag_status == 0:
				return StepStatus.Running

		return StepStatus.Success

	def pre__stop_hot_standby_database_replication(self):
		"""Stop Hot Standby Database Replication"""
		self.hot_standby_database_server_doc.stop_replication()
		return StepStatus.Success

	def pre__stop_other_replica_database_replication(self):
		"""Stop Other Replica Database Replication"""
		for replica in self.replica_database_server_docs:
			replica.stop_replication()
		return StepStatus.Success

	def pre__disable_read_only_mode_from_database_server(self):
		"""Disable Read Only Mode From Database Server"""
		self.database_server_doc.disable_read_only_mode(update_variables_synchronously=True)
		return StepStatus.Success

	#########################################################
	#                Post Migrate Steps                     #
	#########################################################
	def post__archive_hot_standby_database_server(self):
		"""Archive Hot Standby Database Server"""

		# Don't block the flow for archival failure
		# TODO: Add some retry mechanism to archive the server later
		try:
			self.hot_standby_database_server_doc.archive()
			row = None
			for s in self.servers:
				if s.current_role == "Hot Standby":
					row = s
					break
			if row:
				row.archived = 1
				self.save()
		except Exception:
			self.add_comment(
				"Comment",
				"Error archiving hot standby database server - " + self.hot_standby_database_server,
			)

		return StepStatus.Success

	def post__activate_sites(self):
		"""Activate Sites"""
		status = self.activate_site()
		if status == "Success":
			return StepStatus.Success
		if status == "Failure":
			return StepStatus.Failure
		return StepStatus.Running

	def post__enable_replication_on_replica(self):
		"""Enable Replication On Replica"""
		for replica in self.replica_database_server_docs:
			replica.start_replication()
		return StepStatus.Success

	# change function name
	def post__wait_for_minimal_replication_lag_of_replica(self):
		"""Wait For Minimal Replication Lag Of Replica"""

		"""
		TODO:
		Failure in this should not trigger a site recovery
		Just throw the replica.
		"""

		for replica in self.replica_database_server_docs:
			lag_status = check_replication_lag(replica, 300)
			if lag_status == -1:
				return StepStatus.Failure
			if lag_status == 0:
				return StepStatus.Running

		return StepStatus.Success

	def post__restore_replication_configuration_of_site_and_bench(self):
		"""Restore Replication Configuration Of Site And Bench"""
		self.add_replication_config_to_site_and_bench()
		return StepStatus.Success

	#########################################################
	#                    Failover Steps                     #
	#########################################################
	def failover__plan_and_assign_new_role_to_servers(self):
		"""Plan And Assign New Role To Servers"""
		hot_standby_server = next((s for s in self.servers if s.current_role == "Hot Standby"), None)
		if hot_standby_server:
			hot_standby_server.new_role = "Master"

		old_primary_server = next((s for s in self.servers if s.current_role == "Master"), None)
		if old_primary_server:
			old_primary_server.new_role = "Retired"

		replica_servers = [s for s in self.servers if s.current_role == "Replica"]
		for s in replica_servers:
			s.new_role = "Replica"

		self.save()
		return StepStatus.Success

	def failover__configure_hot_standby_database_server_as_new_master(self):
		"""Configure Hot Standby Database Server As New Master"""
		self.hot_standby_database_server_doc.reset_replication()
		return StepStatus.Success

	def failover__update_reference_to_new_master_database_server(self):
		"""Update Reference To New Master Database Server"""
		server = self.app_server_doc
		server.database_server = self.hot_standby_database_server
		server.save()
		return StepStatus.Success

	def failover__update_new_master_database_server_plan_and_team(self):
		"""Update New Master Database Server Plan And Team"""
		# Update the plan and team of the new master database server
		server = self.hot_standby_database_server_doc
		old_db = self.database_server_doc
		server.plan = old_db.plan  # Handle arm , x86_64 plans automatically
		server.team = old_db.team
		server.title = old_db.title
		server.save()
		return StepStatus.Success

	def failover__gather_binlog_position_from_new_master(self):
		"""Gather Binlog Position From New Master Database Server"""
		self.initial_binlog_position_of_new_primary_db = (
			self.hot_standby_database_server_doc.get_replication_status()
			.get("data", {})
			.get("gtid_current_pos", "")
		)
		if not self.initial_binlog_position_of_new_primary_db:
			frappe.throw("Failed to gather initial binlog position from new master database server")
		self.save()
		return StepStatus.Success

	def failover__update_master_database_ref_in_replica_servers(self):
		"""Update Master Database Info In Replica Servers"""
		for replica in self.replica_database_server_docs:
			frappe.db.set_value("Database Server", replica.name, "primary", self.hot_standby_database_server)
		return StepStatus.Success

	def failover__disable_read_only_mode_on_new_master(self):
		"""Disable Read Only Mode From New Master Database Server"""
		self.hot_standby_database_server_doc.disable_read_only_mode(update_variables_synchronously=True)
		return StepStatus.Success

	def failover__wait_for_master_database_server_to_be_available(self):
		"""Wait For Master Database Server To Be Available"""
		if self.hot_standby_database_server_doc.ping_mariadb():
			return StepStatus.Success

		return StepStatus.Running

	def failover__configure_sites_with_new_master_database_server(self):
		"""Configure Sites With New Master Database Server"""

		# Check if any deactivate site job already exists
		if frappe.db.count(
			"Agent Job",
			{
				"job_type": "Update Database Host",
				"reference_doctype": self.doctype,
				"reference_name": self.name,
			},
		):
			status = frappe.db.get_value(
				"Agent Job",
				{
					"job_type": "Update Database Host",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
				},
				"status",
				order_by="modified desc",
			)
			if status in ("Pending", "Running"):
				return StepStatus.Running
			if status == "Success":
				return StepStatus.Success
			if status == "Failure":
				return StepStatus.Failure

		agent = self.app_server_doc.agent
		"""
		On changing the database server on server doctype, it should automatically update the database host
		in all the benches that are associated with this server.

		Do a check here in this doctype as well to reduce chance of affecting by external changes.
		"""

		hot_standby_database_server = self.hot_standby_database_server

		benches = frappe.get_all("Bench", {"server": self.server, "status": ("!=", "Archived")})
		for bench in benches:
			bench: "Bench" = frappe.get_doc("Bench", bench)
			if bench.database_server != hot_standby_database_server:
				# We will do a bulk update, So avoid automatically triggering update bench config job
				bench.flags.avoid_triggerring_update_bench_config_job = True
				bench.database_server = hot_standby_database_server
				bench.save()

		agent.update_database_host_in_all_benches(
			self.hot_standby_database_server_doc.private_ip, self.doctype, self.name
		)
		return StepStatus.Running

	def failover__activate_sites(self):
		"""Activate Sites"""
		return self.post__activate_sites()

	def failover__join_other_replicas_to_new_master(self):
		"""Join Other Replicas To New Master"""
		for replica in self.new_replica_database_server_docs:
			replica.configure_replication(gtid_slave_pos=self.initial_binlog_position_of_new_primary_db)
		return StepStatus.Success

	def failover__start_replication_on_replica(self):
		"""Start Replication On Replica"""
		for replica in self.new_replica_database_server_docs:
			replica.start_replication()
		return StepStatus.Success

	def failover__wait_for_minimal_replication_lag_of_replica(self):
		"""Wait For Minimal Replication Lag Of Replica"""

		for replica in self.new_replica_database_server_docs:
			lag_status = check_replication_lag(replica, 300)
			if lag_status == -1:
				return StepStatus.Failure
			if lag_status == 0:
				return StepStatus.Running

		return StepStatus.Success

	def failover__restore_replication_configuration_of_site_and_bench(self):
		"""Restore Replication Configuration Of Site And Bench"""
		return self.post__restore_replication_configuration_of_site_and_bench()

	def failover__archive_old_primary_database_server(self):
		"""Archive Old Primary Database Server"""
		# Just unset team / plan / disable subscription
		try:
			self.database_server_doc.archive()
			row = None
			for s in self.servers:
				if s.current_role == "Master":
					row = s
					break
			if row:
				row.archived = 1
				self.save()
		except Exception:
			self.add_comment(
				"Comment",
				"Error archiving primary database server - " + self.database_server,
			)
		return StepStatus.Success

	def failover__create_subscription_for_new_master(self):
		"""Create Subscription For New Master Database Server"""
		return StepStatus.Success

	#########################################################
	#              Common Steps / Private Methods           #
	#########################################################
	def deactivate_site(self):
		# Check if any deactivate site job already exists
		if frappe.db.count(
			"Agent Job",
			{
				"site": self.site,
				"job_type": "Deactivate Site",
				"reference_doctype": self.doctype,
				"reference_name": self.name,
			},
		):
			return frappe.db.get_value(
				"Agent Job",
				{
					"site": self.site,
					"job_type": "Deactivate Site",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
				},
				"status",
				order_by="modified desc",
			)

		# Deactivate the site
		self.app_server_doc.agent.deactivate_site(
			self.site_doc, reference_doctype=self.doctype, reference_name=self.name
		)
		return "Pending"

	def activate_site(self):
		if frappe.db.count(
			"Agent Job",
			{
				"site": self.site,
				"job_type": "Activate Site",
				"reference_doctype": self.doctype,
				"reference_name": self.name,
			},
		):
			return frappe.db.get_value(
				"Agent Job",
				{
					"site": self.site,
					"job_type": "Activate Site",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
				},
				"status",
				order_by="modified desc",
			)

		self.app_server_doc.agent.activate_site(
			self.site_doc, reference_doctype=self.doctype, reference_name=self.name
		)
		return "Pending"

	def store_db_replication_config_of_site(self, save: bool = True):
		config = {}
		site = self.site_doc
		for key in REPLICATION_CONFIG_KEYS:
			value = site.get_config_value_for_key(key)
			if value is not None:
				config[key] = value

		self.site_replication_config = json.dumps(config, indent=2)
		if save:
			self.save()

	def store_replication_config_of_bench(self, save: bool = True):
		config = {}
		common_site_config: dict = json.loads(self.release_group_doc.common_site_config)
		for key in REPLICATION_CONFIG_KEYS:
			value = common_site_config.get(key)
			if value is not None:
				config[key] = value

		self.bench_replication_config = json.dumps(config, indent=2)
		if save:
			self.save()

	def remove_replication_config_from_site_and_bench(self):
		site = self.site_doc
		release_group = self.release_group_doc

		site.delete_multiple_config(self.site_replication_config_dict.keys())

		for key in self.bench_replication_config_dict:
			release_group.delete_config(key)

	def add_replication_config_to_site_and_bench(self):
		self.site_doc.update_config(self.site_replication_config_dict)
		self.release_group_doc.update_config(self.bench_replication_config_dict)

	#########################################################
	#                 Internal Methods                      #
	#########################################################
	def populate_server_infos(self):
		self.append(
			"servers",
			{"current_role": "Master", "database_server": self.database_server, "new_role": ""},
		)
		# Find the replica servers
		replica_servers = frappe.get_all(
			"Database Server",
			{"is_primary": False, "primary": self.database_server, "status": "Active"},
			pluck="name",
		)
		for replica in replica_servers:
			self.append(
				"servers",
				{"current_role": "Replica", "database_server": replica, "new_role": ""},
			)

		# Do validation that the database server doesn't have any broken replication
		if frappe.db.count(
			"Database Server",
			{
				"primary": self.database_server,
				"is_primary": 0,
				"status": ("in", ["Pending", "Installing", "Broken"]),
			},
		):
			frappe.throw(
				f"Database Server {self.database_server} has few inactive replicas. Please fix it before proceeding."
			)

	def add_steps(self):
		for step in self.pre_migrate_steps__template:
			step.update({"status": "Pending"})
			self.append("pre_migrate_steps", step)

		for step in self.post_migrate_steps__template:
			step.update({"status": "Pending"})
			self.append("post_migrate_steps", step)

		for step in self.failover_steps__template:
			step.update({"status": "Pending"})
			self.append("failover_steps", step)

	def callback_to_linked_site_update(self):
		from press.press.doctype.site_update.site_update import (
			process_callback_from_logical_replication_backup,
		)

		process_callback_from_logical_replication_backup(self)

	@frappe.whitelist()
	def execute(self):
		if self.stage_status == "Running":
			frappe.msgprint("Replication is already in Running state. It will be executed soon.")
			return
		# Just set to Running, scheduler will pick it up
		self.stage_status = "Running"
		if not self.start:
			self.start = frappe.utils.now_datetime()
		self.save()
		self.next()

	def fail(self, save: bool = True) -> None:
		self.stage_status = "Failure"
		for step in self.current_execution_steps:
			if step.stage_status == "Pending":
				step.stage_status = "Skipped"
		self.end = frappe.utils.now_datetime()
		self.duration = frappe.utils.cint((self.end - self.start).total_seconds())
		if save:
			self.save(ignore_version=True)

	def finish(self) -> None:
		# if stage_status is already Success or Failure, then don't update the stage_status and durations
		if self.stage_status not in ("Success", "Failure"):
			self.stage_status = "Success" if self.is_restoration_steps_successful() else "Failure"
			self.end = frappe.utils.now_datetime()
			self.duration = frappe.utils.cint((self.end - self.start).total_seconds())

		self.save()

	@frappe.whitelist()
	def next(self) -> None:
		if self.stage_status != "Running" and self.stage_status not in ("Success", "Failure"):
			self.stage_status = "Running"
			self.save(ignore_version=True)

		next_step_to_run = None

		# Check if current_step is running
		current_running_step = self.current_running_step
		if current_running_step:
			next_step_to_run = current_running_step
		elif self.next_step:
			next_step_to_run = self.next_step

		if not next_step_to_run:
			# We've executed everything
			self.finish()
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step_to_run.name,
			enqueue_after_commit=True,
			deduplicate=next_step_to_run.wait_for_completion
			is False,  # Don't deduplicate if wait_for_completion is True
			job_id=f"logical_replication||{self.name}||{next_step_to_run.name}",
			timeout=600,
		)

	@frappe.whitelist(allow_guest=True)
	def retry(self):
		# Reset the states
		self.stage_status = "Pending"
		if not self.start:
			self.start = frappe.utils.now_datetime()
		self.end = None
		self.duration = None
		for step in self.current_execution_steps:
			step.status = "Pending"
		self.save(ignore_version=True)

	@frappe.whitelist()
	def force_continue(self) -> None:
		# Mark all failed and skipped steps as pending
		for step in self.current_execution_steps:
			if step.status in ("Failure", "Skipped"):
				step.status = "Pending"

		self.stage_status = "Running"
		self.save()

		self.next()

	@frappe.whitelist()
	def force_fail(self) -> None:
		# Mark all pending steps as failure
		for step in self.current_execution_steps:
			if step.status == "Pending":
				step.status = "Failure"
		self.stage_status = "Failure"
		self.save()

	@property
	def current_execution_steps(self) -> list["LogicalReplicationStep"]:
		if self.execution_stage == "Pre-Migrate":
			return self.pre_migrate_steps
		if self.execution_stage == "Post-Migrate":
			return self.post_migrate_steps
		if self.execution_stage == "Failover":
			return self.failover_steps

		frappe.throw(f"Invalid execution stage: {self.execution_stage}")
		return None  # type: ignore[return-value]

	@property
	def current_running_step(self) -> "LogicalReplicationStep | None":
		for step in self.current_execution_steps:
			if step.status == "Running":
				return step
		return None

	@property
	def next_step(self) -> "LogicalReplicationStep | None":
		for step in self.current_execution_steps:
			if step.status == "Pending":
				return step
		return None

	def is_restoration_steps_successful(self) -> bool:
		return all(step.status == "Success" for step in self.current_execution_steps)

	@frappe.whitelist()
	def execute_step(self, step_name):
		step = self.get_step(step_name)

		if not step.start:
			step.start = frappe.utils.now_datetime()
		try:
			result = getattr(self, step.method)()
			step.status = result.name
			"""
			If the step is async and function has returned Running,
			Then save the document and return

			Some external process will resume the job later
			"""
			if step.is_async and result == StepStatus.Running:
				self.save(ignore_version=True)
				return

			"""
			If the step is sync and function is marked to wait for completion,
			Then wait for the function to complete
			"""
			if step.wait_for_completion and result == StepStatus.Running:
				step.attempts = step.attempts + 1 if step.attempts else 1
				self.save(ignore_version=True)
				time.sleep(1)

		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = frappe.utils.now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail(save=True)
		else:
			self.save(ignore_version=True)
			self.next()

	def get_step(self, step_name) -> "LogicalReplicationStep | None":
		for step in self.current_execution_steps:
			if step.name == step_name:
				return step
		return None

	def get_step_by_method(self, method_name) -> "LogicalReplicationStep | None":
		for step in self.current_execution_steps:
			if step.method == method_name:
				return step
		return None

	def ansible_run(self, command):
		vm = {
			"ip": self.virtual_machine.public_ip_address,
			"private_ip": self.virtual_machine.private_ip_address,
			"cluster": self.virtual_machine.cluster,
		}
		result = AnsibleAdHoc(sources=[vm]).run(command, self.name)[0]
		self.add_command(command, result)
		return result

	def add_command(self, command, result):
		pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
		comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
		self.add_comment(text=comment)


def process_logical_replication_backup_deactivate_site_job_update(job):
	if job.reference_doctype != "Logical Replication Backup":
		return
	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return
	doc: LogicalReplicationBackup = frappe.get_doc("Logical Replication Backup", job.reference_name)
	doc.next()


def process_logical_replication_backup_activate_site_job_update(job):
	if job.reference_doctype != "Logical Replication Backup":
		return
	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return
	doc: LogicalReplicationBackup = frappe.get_doc("Logical Replication Backup", job.reference_name)
	doc.next()


def process_logical_replication_backup_update_database_host_job_update(job):
	if job.reference_doctype != "Logical Replication Backup":
		return
	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return
	doc: LogicalReplicationBackup = frappe.get_doc("Logical Replication Backup", job.reference_name)
	doc.next()


def get_logical_replication_backup_restoration_steps(
	name: str, stage: Literal["Pre-Migrate", "Post-Migrate", "Failover"]
) -> list[dict]:
	"""
	{
		"title": "Step Name",
		"status": "Success",
		"output": "Output",
		"stage": "Restore Backup"
	}
	"""
	parent_field = {
		"Pre-Migrate": "pre_migrate_steps",
		"Post-Migrate": "post_migrate_steps",
		"Failover": "failover_steps",
	}[stage]
	steps = frappe.get_all(
		"Logical Replication Step",
		{
			"parent": name,
			"parenttype": "Logical Replication Backup",
			"parentfield": parent_field,
		},
		["name", "step", "status", "traceback"],
		order_by="idx",
	)

	return [
		{
			"title": step["step"],
			"status": step["status"],
			"output": "" if not step.get("traceback") else step["traceback"],
			"stage": stage.replace("-", " "),
			"name": step["name"],
		}
		for step in steps
	]
