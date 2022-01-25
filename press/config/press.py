from frappe import _


def get_data():
	return [
		{
			"label": _("Components"),
			"items": [
				{"type": "doctype", "name": "Proxy Server"},
				{"type": "doctype", "name": "Server"},
				{"type": "doctype", "name": "Bench"},
				{"type": "doctype", "name": "Site"},
				{"type": "doctype", "name": "Account Request"},
			],
		},
		{
			"label": _("Agent"),
			"items": [
				{"type": "doctype", "name": "Agent Job"},
				{"type": "doctype", "name": "Agent Job Step"},
				{"type": "doctype", "name": "Agent Job Type"},
			],
		},
		{
			"label": _("Setup"),
			"items": [
				{"type": "doctype", "name": "Plan"},
				{"type": "doctype", "name": "App"},
				{"type": "doctype", "name": "Release Group"},
				{"type": "doctype", "name": "App Release"},
				{"type": "doctype", "name": "Deploy Candidate"},
			],
		},
		{"label": _("Domains"), "items": [{"type": "doctype", "name": "Custom Domain"}]},
		{
			"label": _("Payments"),
			"items": [
				{"type": "doctype", "name": "Credit Ledger Entry"},
				{"type": "doctype", "name": "Payment"},
				{"type": "doctype", "name": "Payment Provision"},
				{"type": "doctype", "name": "Usage Report"},
			],
		},
		{
			"label": _("Deploy"),
			"items": [
				{"type": "doctype", "name": "Site Deploy"},
				{"type": "doctype", "name": "Bench Deploy"},
			],
		},
	]
