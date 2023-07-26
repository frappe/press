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
@protected("Code Server")
def code_server_password(name):
	code_server = frappe.get_doc("Code Server", name)
	return code_server.get_password("password")


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
