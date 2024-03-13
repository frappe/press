import time

import frappe
from dns.resolver import Resolver

from press.api.server import plans
from press.runner import Ansible
from press.utils import get_current_team
from press.api.site import NAMESERVERS
from frappe.utils import strip


@frappe.whitelist()
def new(server):
	server_details = frappe._dict(server)

	team = get_current_team(get_doc=True)
	validate_team(team)

	proxy_server = get_proxy_server_for_cluster()

	return create_self_hosted_server(server_details, team, proxy_server)


def create_self_hosted_server(server_details, team, proxy_server):
	try:
		self_hosted_server = frappe.new_doc(
			"Self Hosted Server",
			**{
				"ip": strip(server_details.get("app_public_ip", "")),
				"private_ip": strip(server_details.get("app_private_ip", "")),
				"mariadb_ip": strip(server_details.get("db_public_ip", "")),
				"mariadb_private_ip": strip(server_details.get("db_private_ip", "")),
				"title": server_details.title,
				"proxy_server": proxy_server,
				"proxy_created": True,
				"different_database_server": True,
				"team": team.name,
				"plan": server_details.plan["name"],
				"database_plan": server_details.plan["name"],
				"new_server": True,
			}
		).insert()
	except frappe.DuplicateEntryError as e:
		# Exception return  tupple like ('Self Hosted Server', 'SHS-00018.cloud.pressonprem.com')
		server_name = e.args[1]
		return server_name

	return self_hosted_server.name


def validate_team(team):
	if not team:
		frappe.throw("You must be part of a team to create a new server")

	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	if not team.self_hosted_servers_enabled:
		frappe.throw(
			"You cannot create a new server because Hybrid Cloud is disabled for your account. Please contact support to enable it."
		)


def get_proxy_server_for_cluster(cluster=None):
	cluster = get_hybrid_cluster() if not cluster else cluster

	return frappe.get_all("Proxy Server", {"cluster": cluster}, pluck="name")[0]


def get_hybrid_cluster():
	return frappe.db.get_value("Cluster", {"hybrid": 1}, "name")


@frappe.whitelist()
def sshkey():
	return frappe.db.get_value("SSH Key", {"enabled": 1, "default": 1}, "public_key")


@frappe.whitelist()
def verify(server):
	play_status = "Failure"
	server_doc = frappe.get_doc("Self Hosted Server", server)
	_server_details = frappe._dict(
		{
			"ssh_user": server_doc.ssh_user,
			"ssh_port": server_doc.ssh_port,
			"doctype": "Self Hosted Server",
			"name": server_doc.name,
		}
	)

	app_server_result = verify_app_server_is_reachable(_server_details, server_doc)
	db_server_result = verify_db_server_is_reachable(_server_details, server_doc)

	if server_doc.different_database_server:
		# If both servers are reachable, then the status is success
		if app_server_result.status == "Success" and db_server_result.status == "Success":
			play_status = "Success"

	else:
		if app_server_result.status == "Success":
			play_status = "Success"

			server_doc.fetch_private_ip()
			server_doc.fetch_system_ram(app_server_result.name)
			server_doc.fetch_system_specifications(app_server_result.name)
			server_doc.check_minimum_specs()
			server_doc.save()

	if play_status == "Success":
		server_doc.reload()
		server_doc.status = "Pending"
		server_doc.save()

		server_doc.reload()
		server_doc.create_database_server()

		server_doc.reload()
		server_doc.create_application_server()

		return True
	else:
		return False


def verify_app_server_is_reachable(_server_details, server_doc):
	ping_app_server = Ansible(
		playbook="ping.yml",
		server=_server_details.update({"ip": server_doc.ip}),
	)
	return ping_app_server.run()


def verify_db_server_is_reachable(_server_details, server_doc):
	if not server_doc.different_database_server:
		return frappe._dict({"status": "Success"})

	ping_db_server = Ansible(
		playbook="ping.yml",
		server=_server_details.update({"ip": server_doc.mariadb_ip}),
	)
	return ping_db_server.run()


@frappe.whitelist()
def setup(server):
	server_doc = frappe.get_doc("Self Hosted Server", server)
	server_doc.start_setup = True
	server_doc.save()
	server_doc.setup_server()
	time.sleep(1)


@frappe.whitelist()
def get_plans():
	server_plan = plans("Self Hosted Server")
	return server_plan


@frappe.whitelist()
def check_dns(domain, ip):
	try:
		resolver = Resolver(configure=False)
		resolver.nameservers = NAMESERVERS
		domain_ip = resolver.query(domain.strip(), "A")[0].to_text()
		if domain_ip == ip:
			return True
	except Exception:
		return False
	return False
