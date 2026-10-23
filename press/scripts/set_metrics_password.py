# In bench IPython console:  %run press/scripts/set_metrics_password.py
# Sets one metrics scrape password on several dedicated servers of a team, then
# use set_metrics_password([("Server", "f1-x.frappe.cloud"), ("Database Server", "m1-x.frappe.cloud")]).
# The team scrapes https://<server>/metrics/<exporter> with user `customer` and the printed password.
import frappe

from press.runner import Ansible

USERNAME = "customer"  # never "frappe": that is the central monitoring user


def set_on_server(doctype, name, password):
	server = frappe.get_doc(doctype, name)
	if server.public:
		raise Exception(f"{name} is public, its metrics show other teams' benches")
	return Ansible(
		playbook="monitoring_password.yml",
		server=server,
		user=server._ssh_user(),
		port=server._ssh_port(),
		variables={"monitoring_username": USERNAME, "monitoring_password": password},
	).run()


def set_metrics_password(servers, password=None):
	"""Pass the same password again to retry a failed server or to add one more."""
	password = password or frappe.generate_hash()
	print("password:", password)  # first, so a failed server does not hide it
	for doctype, name in servers:
		print(name, set_on_server(doctype, name, password).status)
	return password
