import time

import frappe
from dns.resolver import Resolver

from press.api.server import plans
from press.runner import Ansible
from press.utils import get_current_team
from press.api.site import NAMESERVERS


@frappe.whitelist()
def new(server):
	team = get_current_team(get_doc=True)

	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")

	if not team.self_hosted_servers_enabled:
		frappe.throw(
			"You cannot create a new server because Hybrid Cloud is disabled for your account. Please contact support to enable it."
		)

	cluster = get_cluster()
	proxy_server = get_proxy_server_for_cluster(cluster)

	ip_details = get_sanitized_ip(server)
	print(ip_details)

	is_multi_server_setup = True

	if server["setupType"] == "standalone":
		is_multi_server_setup = False

	self_hosted_server = frappe.new_doc(
		"Self Hosted Server",
		**{
			"ip": ip_details.public_ip,
			"private_ip": ip_details.private_ip,
			"mariadb_ip": ip_details.db_public_ip,
			"mariadb_private_ip": ip_details.db_private_ip,
			"title": server["title"],
			"proxy_server": proxy_server,
			"proxy_created": True,
			"different_database_server": is_multi_server_setup,
			"team": team.name,
			"plan": server["plan"]["name"],
			"database_plan": server["plan"]["name"],
			"new_server": True,
		}
	).insert()

	return self_hosted_server.name


def get_sanitized_ip(server):
	return frappe._dict(
		{
			"public_ip": server["publicIP"].strip(),
			"private_ip": server["privateIP"].strip() if server["privateIP"] else None,
			"db_public_ip": server["dbpublicIP"].strip(),
			"db_private_ip": server["dbprivateIP"].strip() if server["dbprivateIP"] else None,
		}
	)


def get_proxy_server_for_cluster(cluster):
	return frappe.get_all("Proxy Server", {"cluster": cluster}, pluck="name")[0]


def get_cluster():
	return frappe.db.get_value("Cluster", {"hybrid": 1}, "name")


@frappe.whitelist()
def sshkey():
	return frappe.db.get_value("SSH Key", {"enabled": 1, "default": 1}, "public_key")


@frappe.whitelist()
def verify(server):
	play_status = "Failure"
	server = "SHS-00002.cloud.pressonprem.com"
	server_doc = frappe.get_doc("Self Hosted Server", server)

	if server_doc.different_database_server:
		server = frappe._dict(
			{
				"ssh_user": server_doc.ssh_user,
				"ssh_port": server_doc.ssh_port,
				"doctype": "Self Hosted Server",
				"name": server_doc.name,
			}
		)

		# Check if the server is reachable
		ping_app_server = Ansible(
			playbook="ping.yml",
			server=server.update({"ip": server_doc.ip}),
		)
		app = ping_app_server.run()

		# Check if the database server is reachable
		ping_db_server = Ansible(
			playbook="ping.yml",
			server=server.update({"ip": server_doc.mariadb_ip}),
		)
		db = ping_db_server.run()

		# If both servers are reachable, then the status is success
		if app.status == "Success" and db.status == "Success":
			play_status = "Success"

	else:
		ansible = Ansible(
			playbook="ping.yml",
			server=server_doc,
		)
		play = ansible.run()
		play_status = play.status

		if play_status == "Success":
			server_doc.fetch_private_ip()
			server_doc.fetch_system_ram(play.name)
			server_doc.fetch_system_specifications(play.name)
			server_doc.check_minimum_specs()
			server_doc.save()

	if play_status == "Success":
		server_doc.reload()
		server_doc.status = "Pending"
		server_doc.save()
		server_doc.create_db_server()
		server_doc.reload()
		server_doc.create_server()
		server_doc.reload()
		return True
	else:
		return False


@frappe.whitelist()
def setup_nginx(server):
	server_doc = frappe.get_doc("Self Hosted Server", server)
	return server_doc.setup_nginx()


@frappe.whitelist()
def setup(server):
	server_doc = frappe.get_doc("Self Hosted Server", server)
	server_doc.start_setup = True
	server_doc.create_subscription()
	server_doc.create_tls_certs()
	server_doc.save()
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
