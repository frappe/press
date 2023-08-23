import frappe
from press.utils import get_current_team
from press.api.site import protected

from typing import Dict, List


@frappe.whitelist()
def spaces(space_filter: Dict | None) -> Dict:
	"""
	Returns all spaces and code servers for the current team
	"""
	if space_filter is None:
		space_filter = {"status": ""}

	CodeServer = frappe.qb.DocType("Code Server")
	ReleaseGroup = frappe.qb.DocType("Release Group")

	servers_query = (
		frappe.qb.from_(CodeServer)
		.select(
			CodeServer.name,
			CodeServer.status,
			CodeServer.creation,
			CodeServer.bench,
			ReleaseGroup.title,
		)
		.left_join(ReleaseGroup)
		.on(CodeServer.group == ReleaseGroup.name)
		.orderby(CodeServer.creation, order=frappe.qb.desc)
	)

	if space_filter["status"] == "Active":
		servers_query = servers_query.where(CodeServer.status == "Active")
	elif space_filter["status"] == "Broken":
		servers_query = servers_query.where(CodeServer.status == "Broken")
	else:
		servers_query = servers_query.where(CodeServer.status != "Archived")

	return {
		"spaces": {},
		"servers": servers_query.run(as_dict=True),
	}


@frappe.whitelist()
def code_server_domain():
	"""
	Returns the domain for code servers
	"""
	return frappe.db.get_single_value("Press Settings", "spaces_domain")


@frappe.whitelist()
def code_server_group_options():
	return frappe.get_all(
		"Release Group",
		{"team": get_current_team(), "public": False, "enabled": True},
		["name", "title"],
	)


@frappe.whitelist()
def code_server_bench_options(group):
	valid_candidates = frappe.get_all(
		"Deploy Candidate",
		filters=[
			["Deploy Candidate Build Step", "step", "like", "%Code Server%"],
			["Deploy Candidate", "group", "=", group],
			["Deploy Candidate", "team", "=", get_current_team()],
		],
		pluck="name",
	)
	return frappe.get_all(
		"Bench",
		{"status": "Active", "group": group, "candidate": ("in", valid_candidates)},
		pluck="name",
		order_by="creation desc",
	)


@frappe.whitelist()
@protected("Code Server")
def code_server(name):
	return frappe.get_doc("Code Server", name)


@frappe.whitelist()
@protected("Code Server")
def stop_code_server(name) -> None:
	frappe.get_doc("Code Server", name).stop()


@frappe.whitelist()
@protected("Code Server")
def start_code_server(name) -> None:
	frappe.get_doc("Code Server", name).start()


@frappe.whitelist()
def code_server_password(name) -> str:
	if get_current_team() != frappe.db.get_value("Code Server", name, "team"):
		frappe.throw("Not allowed", frappe.PermissionError)
	return frappe.utils.password.get_decrypted_password("Code Server", name, "password")


@frappe.whitelist()
@protected("Code Server")
def drop_code_server(name) -> None:
	frappe.get_doc("Code Server", name).archive()


@frappe.whitelist()
def create_code_server(subdomain, domain, bench) -> str:
	"""
	Create a new code server doc
	"""
	team = get_current_team()
	if not frappe.db.get_value("Team", team, "code_servers_enabled"):
		return

	code_server = frappe.get_doc(
		{
			"doctype": "Code Server",
			"subdomain": subdomain,
			"bench": bench,
			"domain": domain,
			"team": team,
		}
	).insert(ignore_permissions=True)
	return code_server.name


@frappe.whitelist()
def exists(subdomain, domain) -> bool:
	"""
	Checks if a subdomain is already taken
	"""
	banned_domains = frappe.get_all("Blocked Domain", {"block_for_all": 1}, pluck="name")
	if banned_domains and subdomain in banned_domains:
		return True
	else:
		return bool(
			frappe.db.exists("Blocked Domain", {"name": subdomain, "root_domain": domain})
			or frappe.db.exists(
				"Code Server",
				{"subdomain": subdomain, "domain": domain, "status": ("!=", "Archived")},
			)
		)


@frappe.whitelist()
@protected("Code Server")
def code_server_jobs(name, start=0) -> List:
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"code_server": name},
		start=start,
		limit=10,
		order_by="creation desc",
	)
	return jobs
