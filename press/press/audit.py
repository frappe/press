"""Functions for automated audit of frappe cloud systems."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TypedDict

import frappe
from frappe.utils import add_days, rounded, today

from press.agent import Agent
from press.press.doctype.server.server import Server
from press.press.doctype.site.site import TRANSITORY_STATES
from press.press.doctype.subscription.subscription import (
	created_usage_records,
	paid_plans,
	sites_with_free_hosting,
)


class ServerPlanInfo(TypedDict):
	name: str
	plan: str
	machine_type: str
	vm_memory: float
	plan_memory: float
	vm_disk_size: float
	plan_disk_size: float


class Discrepancies(TypedDict):
	machine_type: list[str]
	memory: list[str]
	disk_size: list[str]


class Audit:
	"""
	Base class for all types of Audit.

	`audit_type` member variable needs to be set to log
	"""

	audit_type = ""

	def log(
		self, log: dict, status: str, telegram_group: str | None = None, telegram_topic: str | None = None
	):
		frappe.get_doc(
			{
				"doctype": "Audit Log",
				"log": json.dumps(log, indent=2),
				"status": status,
				"audit_type": self.audit_type,
				"telegram_group": telegram_group,
				"telegram_topic": telegram_topic,
			}
		).insert()


def get_benches_in_server(server: str) -> dict:
	agent = Agent(server)
	return agent.get("/benches")


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

	audit_type = "Bench Field Check"

	def __init__(self):
		log = {}
		self.server_map = {}
		self.press_map = {}
		status = "Success"

		self.generate_server_map()
		self.generate_press_map()

		log = {
			"Summary": None,
			"potential_fixes": {},
			"sites_only_on_press": self.get_sites_only_on_press(),
			"sites_only_on_server": self.get_sites_only_on_server(),
			"sites_on_multiple_benches": self.get_sites_on_multiple_benches(),
		}
		if any(log.values()):
			status = "Failure"

		log["potential_fixes"] = self.get_potential_fixes()
		log["Summary"] = {
			"Potential fixes": sum(len(sites) for sites in log["potential_fixes"].values()),
			"Sites only on press": len(log["sites_only_on_press"]),
			"Sites only on server": len(log["sites_only_on_server"]),
			"Sites on multiple benches": len(log["sites_on_multiple_benches"]),
		}
		self.apply_potential_fixes()

		self.log(log, status)

	def generate_server_map(self):
		servers = Server.get_all_primary_prod()
		for server in servers:
			benches = get_benches_in_server(server)
			if not benches:
				continue
			for bench_name, bench_desc in benches.items():
				for site in bench_desc["sites"]:
					self.server_map.setdefault(site, []).append(bench_name)

	def generate_press_map(self):
		frappe.db.commit()
		sites = frappe.get_all("Site", ["name", "bench"], {"status": ("!=", "Archived")})
		self.press_map = {site.name: site.bench for site in sites}

	def get_sites_only_on_press(self):
		sites = []
		for site, _ in self.press_map.items():
			if site not in self.server_map:
				sites.append(site)
		return sites

	def get_sites_only_on_server(self):
		sites = {}
		for site, benches in self.server_map.items():
			if site not in self.press_map:
				sites[site] = benches[0] if len(benches) == 1 else benches
		return sites

	def get_sites_on_multiple_benches(self):
		sites = {}
		for site, benches in self.server_map.items():
			if len(benches) > 1:
				sites[site] = benches
		return sites

	def get_potential_fixes(self):
		def bench_field_updates():
			fixes = {}
			for site, bench in self.press_map.items():
				server_benches = self.server_map.get(site, [])
				if len(server_benches) == 1 and server_benches[0] != bench:
					fixes[site] = (bench, server_benches[0])
			return fixes

		return {"bench_field_updates": bench_field_updates()}

	def is_site_updating_or_moving(self, site):
		"""
		During SiteUpdate or SiteMigration, the status of the site is changed to Updating or Pending
		"""
		return frappe.db.get_value("Site", site, "status", for_update=True) in TRANSITORY_STATES

	def apply_potential_fixes(self):
		fixes = self.get_potential_fixes()
		for site, benches in fixes["bench_field_updates"].items():
			if self.is_site_updating_or_moving(site):
				continue
			frappe.db.set_value("Site", site, "bench", benches[1])
		frappe.db.commit()


class AppServerReplicaDirsCheck(Audit):
	audit_type = "App Server Replica Dirs Check"

	def __init__(self):
		log = {}
		status = "Success"
		replicas_and_primary = frappe.get_all(
			"Server", {"is_replication_setup": True}, ["name", "primary"], as_list=True
		)
		for replica, primary in replicas_and_primary:
			replica_benches = get_benches_in_server(replica)
			primary_benches = get_benches_in_server(primary)
			for bench, bench_desc in primary_benches.items():
				replica_bench_desc = replica_benches.get(bench)
				if not replica_bench_desc:
					status = "Failure"
					log[bench] = {"Sites on primary only": bench_desc["sites"]}
					continue

				sites_on_primary_only = list(set(bench_desc["sites"]) - set(replica_bench_desc["sites"]))
				if sites_on_primary_only:
					status = "Failure"
					log[bench] = {"Sites on primary only": sites_on_primary_only}
		self.log(log, status)


class BackupRecordCheck(Audit):
	"""Check if latest automated backup records for sites are created."""

	audit_type = "Backup Record Check"
	list_key = "Sites with no backup yesterday"
	backup_summary = "Backup Summary"

	def get_sites_with_backup_in_interval(self, trial_plans: tuple[str]):
		cond_filters = f" AND site.plan NOT IN {trial_plans}" if trial_plans else ""
		return set(
			frappe.db.sql_list(
				f"""
				SELECT
					site.name
				FROM
					`tabSite Backup` site_backup
				JOIN
					`tabSite` site
				ON
					site_backup.site = site.name
				WHERE
					site.status = "Active" and
					site_backup.owner = "Administrator" and
					DATE(site_backup.creation) >= "{self.yesterday}"
					{cond_filters}
			"""
			)
		)

	def get_all_sites(self, trial_plans: tuple[str]):
		filters = {
			"status": "Active",
			"creation": ("<=", datetime.combine(self.yesterday, datetime.min.time())),
			"is_standby": False,
			"skip_scheduled_logical_backups": False,
		}
		if trial_plans:
			filters.update({"plan": ("not in", trial_plans)})
		return set(
			frappe.get_all(
				"Site",
				filters=filters,
				pluck="name",
			)
		)

	def get_sites_activated_yesterday(self):
		from pypika import functions as fn

		site_activites = frappe.qb.DocType("Site Activity")
		return set(
			[
				t[0]
				for t in frappe.qb.from_(site_activites)
				.select(site_activites.site)
				.where(site_activites.action == "Activate Site")
				.where(fn.Date(site_activites.creation) >= self.yesterday)
				.run()
			]
		)

	def __init__(self):
		log = {self.list_key: [], self.backup_summary: {}}
		self.yesterday = frappe.utils.now_datetime().date() - timedelta(days=1)

		trial_plans = tuple(frappe.get_all("Site Plan", dict(is_trial_plan=1), pluck="name"))
		sites_with_backup_in_interval = self.get_sites_with_backup_in_interval(trial_plans)
		all_sites = self.get_all_sites(trial_plans)
		sites_without_backups = (
			all_sites - sites_with_backup_in_interval - self.get_sites_activated_yesterday()
		)
		try:
			success_rate = (len(sites_with_backup_in_interval) / len(all_sites)) * 100
		except ZeroDivisionError:
			success_rate = 0
		summary = {
			"Successful Backups": len(sites_with_backup_in_interval),
			"Failed Backups": len(sites_without_backups),
			"Total Active Sites": len(all_sites),
			"Success Rate": rounded(success_rate, 1),
		}
		log[self.backup_summary] = summary

		if sites_without_backups:
			log[self.list_key] = list(sites_without_backups)
			self.log(log, "Failure")
		else:
			self.log(log, "Success")


class OffsiteBackupCheck(Audit):
	"""Check if files for offsite backup exists on the offsite backup provider."""

	audit_type = "Offsite Backup Check"
	list_key = "Offsite Backup Remote Files unavailable in remote"

	def _get_all_files_in_s3(self) -> list[str]:
		all_files = []
		settings = frappe.get_single("Press Settings")
		s3 = settings.boto3_offsite_backup_session.resource("s3")
		for s3_object in s3.Bucket(settings.aws_s3_bucket).objects.all():
			all_files.append(s3_object.key)
		return all_files

	def __init__(self):
		log = {self.list_key: []}
		status = "Success"
		all_files = self._get_all_files_in_s3()
		offsite_remote_files = frappe.db.sql(
			"""
			SELECT
				remote_file.name, remote_file.file_path, site_backup.site
			FROM
				`tabRemote File` remote_file
			JOIN
				`tabSite Backup` site_backup
			ON
				site_backup.site = remote_file.site
			WHERE
				site_backup.status = "Success" and
				site_backup.files_availability = "Available" and
				site_backup.offsite = True
			""",
			as_dict=True,
		)
		for remote_file in offsite_remote_files:
			if remote_file["file_path"] not in all_files:
				status = "Failure"
				log[self.list_key].append(remote_file)
		self.log(log, status)


def get_teams_with_paid_sites():
	return frappe.get_all(
		"Site",
		{
			"status": ("not in", ("Archived", "Suspended", "Inactive")),
			"free": False,
			"plan": ("in", paid_plans()),
			"trial_end_date": ("is", "not set"),
		},
		pluck="team",
		distinct=True,
	)


class BillingAudit(Audit):
	"""Daily audit of billing related checks"""

	audit_type = "Billing Audit"

	def __init__(self):
		self.paid_plans = paid_plans()
		self.teams_with_paid_sites = frappe.get_all(
			"Site",
			{
				"status": ("not in", ("Archived", "Suspended", "Inactive")),
				"free": False,
				"plan": ("in", self.paid_plans),
				"trial_end_date": ("is", "not set"),
			},
			pluck="team",
			distinct=True,
		)
		audits = {
			"Subscriptions with no usage records created": self.subscriptions_without_usage_record,
			"Disabled teams with active sites": self.disabled_teams_with_active_sites,
			"Sites active after trial": self.free_sites_after_trial,
			"Prepaid Unpaid Invoices with Stripe Invoice ID set": self.prepaid_unpaid_invoices_with_stripe_invoice_id_set,
			"Subscriptions with duplicate usage records created": self.subscriptions_with_duplicate_usage_records,
			"Teams with active sites and unpaid Invoices": self.teams_with_active_sites_and_unpaid_invoices,
		}

		log = {a: [] for a in audits}
		status = "Success"
		for audit_name in audits:
			result = audits[audit_name]()
			log[audit_name] += result
			status = "Failure" if len(result) > 0 else status

		self.log(log=log, status=status, telegram_group="Billing", telegram_topic="Audits")

	def subscriptions_without_usage_record(self):
		free_sites = sites_with_free_hosting()
		free_teams = frappe.get_all("Team", filters={"free_account": True, "enabled": True}, pluck="name")

		return frappe.db.get_all(
			"Subscription",
			filters={
				"team": ("not in", free_teams),
				"enabled": True,
				"plan": ("in", self.paid_plans),
				"name": ("not in", created_usage_records(free_sites, add_days(today(), days=-1))),
				"document_name": ("not in", free_sites),
			},
			pluck="name",
		)

	def subscriptions_with_duplicate_usage_records(self):
		data = frappe.db.sql(
			"""
			SELECT subscription, Count(name) as count
			FROM `tabUsage Record` as UR
			WHERE UR.date = CURDATE()
			AND UR.docstatus = 1
			AND UR.plan NOT LIKE '%Marketplace%'
			GROUP BY UR.document_name, UR.plan, UR.team
			HAVING count > 1
			ORDER BY count DESC
		""",
			as_dict=True,
		)

		if not data:
			return data

		result = []
		for d in data:
			result.append(d.subscription)
		return result

	def disabled_teams_with_active_sites(self):
		return frappe.get_all(
			"Team",
			{"name": ("in", self.teams_with_paid_sites), "enabled": False},
			pluck="name",
		)

	def free_sites_after_trial(self):
		yesterday = add_days(today(), days=-1)
		free_teams = frappe.get_all("Team", {"free_account": 1}, pluck="name")

		filters = {
			"trial_end_date": ["is", "set"],
			"is_standby": 0,
			"plan": ["like", "%Trial%"],
			"status": ("in", ["Active", "Broken"]),
			"team": ("not in", free_teams),
		}

		sites = frappe.db.get_all("Site", filters=filters, fields=["name", "team"], pluck="name")

		# Flake doesn't allow use of duplicate keys in same dictionary
		return frappe.get_all(
			"Site", {"trial_end_date": ["<", yesterday], "name": ("in", sites)}, pluck="name"
		)

	def teams_with_active_sites_and_unpaid_invoices(self):
		today = frappe.utils.getdate()
		# last day of previous month
		last_day = frappe.utils.get_last_day(frappe.utils.add_months(today, -1))

		plan = frappe.qb.DocType("Site Plan")
		query = (
			frappe.qb.from_(plan)
			.select(plan.name)
			.where((plan.enabled == 1) & ((plan.is_frappe_plan == 1) | (plan.is_trial_plan == 1)))
		).run(as_dict=True)
		frappe_plans = [d.name for d in query]

		invoice = frappe.qb.DocType("Invoice")
		team = frappe.qb.DocType("Team")
		site = frappe.qb.DocType("Site")

		query = (
			frappe.qb.from_(invoice)
			.inner_join(team)
			.on(invoice.team == team.name)
			.inner_join(site)
			.on(site.team == team.name)
			.where(
				(site.status).isin(["Active", "Inactive"])
				& (team.enabled == 1)
				& (team.free_account == 0)
				& (invoice.status == "Unpaid")
				& (invoice.docstatus < 2)
				& (invoice.type == "Subscription")
				& (site.free == 0)
				& (site.plan).notin(frappe_plans)
				& (invoice.period_end <= last_day)
			)
			.select(invoice.team)
			.distinct()
		).run(as_dict=True)

		return [d.team for d in query]

	def prepaid_unpaid_invoices_with_stripe_invoice_id_set(self):
		active_teams = frappe.get_all("Team", {"enabled": 1, "free_account": 0}, pluck="name")
		return frappe.get_all(
			"Invoice",
			{
				"status": "Unpaid",
				"payment_mode": "Prepaid Credits",
				"type": "Subscription",
				"team": ("in", active_teams),
				"stripe_invoice_id": ("is", "set"),
			},
			pluck="name",
		)


class PartnerBillingAudit(Audit):
	"""Daily Audit of Partner Billings"""

	audit_type = "Partner Billing Audit"

	def __init__(self):
		audits = {
			"Teams with Paid By Partner mode and billing team not set": self.teams_with_paid_by_partner_and_billing_team_not_set,
			"Paid By Partner Teams with Unpaid Invoices": self.paid_by_partner_teams_with_unpaid_invoices,
		}

		log = {a: [] for a in audits}
		status = "Success"
		for audit_name in audits:
			result = audits[audit_name]()
			log[audit_name] += result
			status = "Failure" if len(result) > 0 else status

		self.log(log=log, status=status, telegram_group="Billing", telegram_topic="Audits")

	def teams_with_paid_by_partner_and_billing_team_not_set(self):
		return frappe.get_all(
			"Team",
			{
				"enabled": True,
				"payment_mode": "Paid By Partner",
				"billing_team": ("is", "not set"),
			},
			pluck="name",
		)

	def paid_by_partner_teams_with_unpaid_invoices(self):
		paid_by_partner_teams = frappe.get_all(
			"Team",
			{
				"enabled": True,
				"payment_mode": "Paid By Partner",
			},
			pluck="name",
		)
		return frappe.get_all(
			"Invoice",
			{
				"status": "Unpaid",
				"team": ("in", paid_by_partner_teams),
				"type": "Subscription",
			},
			pluck="name",
		)


class PlanAudit(Audit):
	audit_type = "Server Plan Sanity Check"

	def audit_plan_discrepancies(self, server_plan_info: list[ServerPlanInfo]):
		"""Check for discrepancies between plan details and actual virtual machine details"""

		messages = {
			"machine_type": "Incorrect machine type compared to server plan",
			"memory": "Incorrect memory compared to server plan",
			"disk_size": "Incorrect disk size compared to server plan",
		}

		discrepancies = {msg: [] for msg in messages.values()}  # type:ignore

		for info in server_plan_info:
			expected_machine_type = info["plan"].split("-")[0]
			if info["machine_type"] != expected_machine_type:
				discrepancies[messages["machine_type"]].append(info["name"])
			if info["vm_memory"] != info["plan_memory"]:
				discrepancies[messages["memory"]].append(info["name"])
			if info["vm_disk_size"] < info["plan_disk_size"]:
				discrepancies[messages["disk_size"]].append(info["name"])

		return discrepancies

	def __init__(self):
		"""Check for plan and virtual machine discrepancies"""
		VirtualMachineDocType = frappe.qb.DocType("Virtual Machine")
		ServerPlan = frappe.qb.DocType("Server Plan")
		server_types = ["Server", "Database Server"]
		server_level_discrepancies = {}

		for server_type in server_types:
			ServerDoctype = frappe.qb.DocType(server_type)
			query = (
				frappe.qb.from_(ServerDoctype)
				.select(
					ServerDoctype.name,
					ServerDoctype.plan,
					VirtualMachineDocType.machine_type,
					VirtualMachineDocType.ram.as_("vm_memory"),
					VirtualMachineDocType.disk_size.as_("vm_disk_size"),
					ServerPlan.disk.as_("plan_disk_size"),
					ServerPlan.memory.as_("plan_memory"),
				)
				.join(VirtualMachineDocType)
				.on(VirtualMachineDocType.name == ServerDoctype.name)
				.join(ServerPlan)
				.on(ServerDoctype.plan == ServerPlan.name)
				.where(ServerDoctype.status == "Active")
				.where(ServerDoctype.is_self_hosted == False)  # noqa: E712
				.where(ServerDoctype.cluster != "Hybrid")
			)
			server_plan_info: list[ServerPlanInfo] = query.run(as_dict=True)
			discrepancies = self.audit_plan_discrepancies(server_plan_info)
			server_level_discrepancies[server_type] = discrepancies

		self.log(
			server_level_discrepancies,
			status="Failure"
			if any(value for category in server_level_discrepancies.values() for value in category.values())
			else "Success",
		)


def check_bench_fields():
	BenchFieldCheck()


def check_backup_records():
	BackupRecordCheck()


def check_offsite_backups():
	OffsiteBackupCheck()


def check_app_server_replica_benches():
	AppServerReplicaDirsCheck()


def plan_audit():
	PlanAudit()


def billing_audit():
	BillingAudit()


def partner_billing_audit():
	PartnerBillingAudit()


def suspend_sites_with_disabled_team():
	site = frappe.qb.DocType("Site")
	team = frappe.qb.DocType("Team")

	disabled_teams_with_active_sites = (
		frappe.qb.from_(site)
		.inner_join(team)
		.on(team.name == site.team)
		.where((site.status).isin(["Active", "Broken", "Pending"]) & (team.enabled == 0))
		.select(site.team)
		.distinct()
		.run(pluck="team")
	)

	if disabled_teams_with_active_sites:
		for team in disabled_teams_with_active_sites:
			frappe.get_doc("Team", team).suspend_sites(reason="Disabled Team")
