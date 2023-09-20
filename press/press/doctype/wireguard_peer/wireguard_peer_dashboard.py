from frappe import _


def get_data():
	return {
		"fieldname": "Server",
		"non_standard_fieldnames": {"Server": "Wireguard Peer"},
		"transactions": [
			{"label": _("Logs"), "items": ["Ansible Play"]},
		],
	}
