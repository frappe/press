import frappe

from press.utils import get_current_team
from press.runner import Ansible
from press.api.server import plans

import dns.resolver


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
			"domain": "self.frappe.dev",
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
	play_doc = frappe.get_doc("Ansible Play", play.name)
	if play_doc.status == "Success":
		server_doc.status = "Pending"
		server_doc.save()
		try:
			frappe.enqueue_doc(
				server_doc.doctype,
				server_doc.name,
				"_setup_nginx",
				queue="long",
				timeout=1200,
				at_front=True,
			)
		except:
			print("Moonji")
		return True
	if play_doc.unreachable:
		return False


@frappe.whitelist()
def setup(server):
	server_doc = frappe.get_doc("Self Hosted Server", server)
	server_doc.create_db_server()
	server_doc.reload()
	server_doc.create_server()
	server_doc.reload()
	start_server_setup(server)


def start_server_setup(server_name):
	server = frappe.get_doc("Server", server_name)
	db = frappe.get_doc("Database Server", server_name)
	server.setup_server()
	db.setup_server()


@frappe.whitelist()
def get_plans():
	server_plan = plans("Self Hosted Server")
	print(server_plan)
	return server_plan


@frappe.whitelist()
def check_dns(domain, ip):
	print(domain, ip)
	try:
		domain_ip = dns.resolver.query(domain, "A")[0].to_text()
		print(domain_ip)
		if domain_ip == ip:
			return True
	except Exception:
		return False
	return False
