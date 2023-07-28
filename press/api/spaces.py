import frappe
from press.utils import get_current_team
from press.api.site import protected


@frappe.whitelist()
def spaces():
	return {
		"spaces": {},
		"servers": frappe.db.sql(
			f"""
				SELECT cs.name, cs.status, cs.creation, cs.bench, rg.title
				FROM `tabCode Server` cs
				LEFT JOIN `tabRelease Group` rg
				ON cs.group = rg.name
				WHERE cs.team = '{get_current_team()}'
				AND cs.status != 'Archived'
				ORDER BY creation DESC""",
			as_dict=True,
		),
	}


@frappe.whitelist()
@protected("Code Server")
def code_server(name):
	return frappe.get_doc("Code Server", name)


@frappe.whitelist()
@protected("Code Server")
def stop_code_server(name):
	frappe.get_doc("Code Server", name).stop()


@frappe.whitelist()
@protected("Code Server")
def start_code_server(name):
	frappe.get_doc("Code Server", name).start()


@frappe.whitelist()
def code_server_password(name):
	if get_current_team() != frappe.db.get_value("Code Server", name, "team"):
		frappe.throw("Not allowed", frappe.PermissionError)
	return frappe.utils.password.get_decrypted_password("Code Server", name, "password")


@frappe.whitelist()
@protected("Code Server")
def drop_code_server(name):
	frappe.get_doc("Code Server", name).archive()


@frappe.whitelist()
@protected("Code Server")
def code_server_jobs(name, start=0):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"code_server": name},
		start=start,
		limit=10,
		order_by="creation desc",
	)
	return jobs


@frappe.whitelist()
def options_for_code_server():
	team = get_current_team()
	groups = frappe.get_all(
		"Release Group", filters={"team": team}, fields=["name", "title"]
	)
	created = frappe.get_all(
		"Code Server",
		filters={"team": team, "status": "Active"},
		pluck="bench",
		order_by="creation desc",
	)

	for group in groups:
		group["benches"] = frappe.get_all(
			"Bench",
			filters={"group": group.name, "status": "Active", "name": ("not in", created)},
			fields=["name"],
		)
	return {
		"groups": groups,
		"domain": frappe.db.get_single_value("Press Settings", "spaces_domain"),
	}


@frappe.whitelist()
def exists(subdomain, domain):
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
def create_code_server(subdomain, domain, bench):
	code_server = frappe.get_doc(
		{
			"doctype": "Code Server",
			"subdomain": subdomain,
			"bench": bench,
			"domain": domain,
			"team": get_current_team(),
		}
	).insert(ignore_permissions=True)
	return code_server.name
