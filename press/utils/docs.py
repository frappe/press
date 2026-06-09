# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
"""Frappe Cloud documentation URLs for user-facing error messages.

A good error explains what happened, tells the user how to fix it, and — when
a relevant guide exists — links to the documentation so the user can self-serve.
See press/utils/dns.py for the reference pattern.

Add a constant here when you link to a doc page from more than one place, or
when the URL is long enough that inlining it hurts readability.
"""

from __future__ import annotations

DOCS_BASE = "https://docs.frappe.io/cloud"

# Sites
CUSTOM_DOMAINS = f"{DOCS_BASE}/sites/custom-domains"
SITE_CONFIG = f"{DOCS_BASE}/sites/site-config"
BACKUPS = f"{DOCS_BASE}/sites/backups"
DATABASE_ACCESS = f"{DOCS_BASE}/sites/database-access"
CREATE_SITE = f"{DOCS_BASE}/sites/creating-a-new-site"
VERSION_UPGRADE = f"{DOCS_BASE}/sites/version-upgrade"
MIGRATE_SITE = f"{DOCS_BASE}/sites/migrate-an-existing-site"
DELETE_SITE = f"{DOCS_BASE}/sites/delete-site"
INSTALL_APP = f"{DOCS_BASE}/installing-an-app"

# Benches
BENCHES = f"{DOCS_BASE}/benches"
CUSTOM_APP = f"{DOCS_BASE}/benches/custom-app"
UPDATE_BENCH = f"{DOCS_BASE}/benches/updating_a_bench"
BENCH_CONFIG = f"{DOCS_BASE}/benches/bench-config"
SSH = f"{DOCS_BASE}/benches/ssh"

# Servers
SERVERS = f"{DOCS_BASE}/servers/servers-introduction"
SERVER_PLAN = f"{DOCS_BASE}/servers/plan"

# Billing
BILLING_PLANS = f"{DOCS_BASE}/billing/plans"
BILL_PAYMENTS = f"{DOCS_BASE}/billing/bill-payments"
PAYMENT_OPTIONS = f"{DOCS_BASE}/billing/payment_options"
DISABLE_ACCOUNT = f"{DOCS_BASE}/billing/disable-account"

# Marketplace
MARKETPLACE = f"{DOCS_BASE}/marketplace"
PUBLISH_APP = f"{DOCS_BASE}/marketplace/publishing-an-app-to-marketplace"
PAYOUTS = f"{DOCS_BASE}/marketplace/payouts"

# Team & account
MANAGE_TEAM = f"{DOCS_BASE}/managing_team_members"
ROLE_PERMISSIONS = f"{DOCS_BASE}/role-permissions"
CHILD_TEAMS = f"{DOCS_BASE}/create-child-teams"
TWO_FACTOR_AUTH = f"{DOCS_BASE}/two-factor-authentication-2fa"


def doc_link(url: str, text: str = "Learn more") -> str:
	"""Render an HTML anchor for embedding in a frappe.throw / msgprint message."""
	return f'<a href="{url}" target="_blank" class="underline">{text}</a>'
