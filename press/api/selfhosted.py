import time

import dns.resolver
import frappe

from press.api.server import plans
from press.runner import Ansible
from press.utils import get_current_team


@frappe.whitelist()
def new(server):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new server because your account is disabled")
	cluster = "Mumbai"
	proxy_server = frappe.get_all("Proxy Server", {"cluster": cluster}, pluck="name")[0]
	self_hosted_server = frappe.get_doc(
		{
			"doctype": "Self Hosted Server",
			"private_ip": server["privateIP"].strip(),
			"ip": server["publicIP"].strip(),
			"title": server["title"],
			"proxy_server": proxy_server,
			"proxy_created": True,
			"team": team.name,
			"plan": server["plan"]["name"],
			"server_url": server["url"],
			"new_server": True,
		}
	).insert()
	return self_hosted_server.name


@frappe.whitelist()
def sshkey():
	key_doc = frappe.get_doc("SSH Key", "Frappe Cloud Production")
	return key_doc.public_key


@frappe.whitelist()
def verify(server):
	server_doc = frappe.get_doc("Self Hosted Server", server)
	ansible = Ansible(
		playbook="ping.yml",
		server=server_doc,
	)
	play = ansible.run()
	if play.status == "Success":
		server_doc.fetch_system_ram(play.name)
		server_doc.status = "Pending"
		server_doc.save()
		server_doc.create_db_server()
		server_doc.reload()
		server_doc.create_server()
		server_doc.reload()
		return True
	if play.unreachable:
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
		domain_ip = dns.resolver.query(domain, "A")[0].to_text()
		if domain_ip == ip:
			return True
	except Exception:
		return False
	return False
