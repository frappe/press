import frappe
from press.utils import get_current_team
from press.runner import Ansible


@frappe.whitelist()
def new(server):
    team = get_current_team(get_doc=True)
    if not team.enabled:
        frappe.throw(
            "You cannot create a new server because your account is disabled")
    cluster = server["cluster"]
    proxy_server = frappe.get_all(
        "Proxy Server", {"cluster": cluster}, pluck="name")[0]
    self_hosted_server = frappe.get_doc(
        {
            "doctype": "Self Hosted Server",
            "private_ip": server["privateIP"],
            "ip": server["publicIP"],
            "title": server["title"],
            "proxy_server": proxy_server,
            "team": team.name,
            "hostname": "s6",
            "domain": "athul.fc.frappe.dev",  # "self.frappe.dev"
        }
    ).insert()
    return self_hosted_server.name


@frappe.whitelist()
def sshkey():
    key_doc = frappe.get_doc("SSH Key", "Frappe Cloud Production")
    print(key_doc.public_key)
    return key_doc.public_key


@frappe.whitelist()
def verify(server):
    server_doc = frappe.get_doc("Self Hosted Server", server)
    ansible = Ansible(
        playbook="ping.yml",
        server=server_doc,
    )
    play = ansible.run()
    return play.name


@frappe.whitelist()
def verify_status(play):
    play_doc = frappe.get_doc("Ansible Play", play)
    if play_doc.status == "Success":
        return True
    if play_doc.unreachable:
        return False
