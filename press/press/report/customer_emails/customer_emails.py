# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

# fmt: off
EU_COUNTRIES = [
	# ── Western Europe ──────────────────────
	"Austria",
	"Belgium",
	"France",
	"Germany",
	"Ireland",
	"Luxembourg",
	"Netherlands",
	"The Netherlands",      # spelling from signup IP lookup

	# ── Northern Europe ─────────────────────
	"Denmark",
	"Estonia",
	"Finland",
	"Latvia",
	"Lithuania",
	"Sweden",

	# ── Southern Europe ─────────────────────
	"Croatia",
	"Cyprus",
	"Republic of Cyprus",   # spelling from signup IP lookup
	"Greece",
	"Italy",
	"Malta",
	"Portugal",
	"Slovenia",
	"Spain",

	# ── Eastern Europe ──────────────────────
	"Bulgaria",
	"Czech Republic",
	"Czechia",              # spelling from signup IP lookup
	"Hungary",
	"Poland",
	"Romania",
	"Slovakia",
]
# fmt: on

# Each region either keeps only these countries, or drops them.
# A customer with no known country is never "in" a country list.
REGIONS = {
	"EU customers": {"include": EU_COUNTRIES},
	"Non-EU customers": {"exclude": EU_COUNTRIES},
	"All customers": {},
}

# Most engaged customers first, so a batched send starts with them
CUSTOMER_TYPES = ["Active", "Inactive", "Signup"]


def execute(filters=None):
	frappe.only_for("System Manager")
	region = (filters or {}).get("region")
	if region not in REGIONS:
		frappe.throw(f"Select a Region. Options: {', '.join(REGIONS)}")

	columns = frappe.get_doc("Report", "Customer Emails").get_columns()
	return columns, get_rows(REGIONS[region])


def get_rows(region: dict) -> list[dict]:
	rows = [row for row in get_customers().values() if is_in_region(row["countries"], region)]
	rows.sort(key=lambda row: (CUSTOMER_TYPES.index(row["customer_type"]), row["email"]))
	return [
		{
			"email": row["email"],
			"customer_type": row["customer_type"],
			"country": ", ".join(sorted(row["countries"])),
			"teams": ", ".join(sorted(row["teams"])),
		}
		for row in rows
	]


def is_in_region(countries: set[str], region: dict) -> bool:
	"""An email used by teams in several countries is in a region if any of them is"""
	if "include" in region:
		return bool(countries & set(region["include"]))
	if "exclude" in region:
		return not countries & set(region["exclude"])
	return True


def get_customers() -> dict[str, dict]:
	"""Every email we hold PII for, merged across the teams and signups it belongs to"""
	customers: dict[str, dict] = {}
	for email, team, country, customer_type in get_contacts():
		email = (email or "").strip().lower()
		if "@" not in email or email.endswith("@deleted.com"):
			continue
		row = customers.setdefault(
			email, {"email": email, "customer_type": customer_type, "countries": set(), "teams": set()}
		)
		row["customer_type"] = min(row["customer_type"], customer_type, key=CUSTOMER_TYPES.index)
		if country:
			row["countries"].add(country)
		if team:
			row["teams"].add(team)
	return customers


def get_contacts() -> list[tuple]:
	"""(email, team, country, customer type) for every place a customer email is stored"""
	signups = frappe.get_all("Account Request", fields=["name", "email", "country"])
	teams, deleted_signups = get_teams({signup.name: signup.country for signup in signups})

	contacts = [(team.user, team.name, team.country, team.customer_type) for team in teams.values()]
	for parent, email in get_team_emails():
		if team := teams.get(parent):
			contacts.append((email, team.name, team.country, team.customer_type))

	# A signup is kept even after its team is deleted, so drop it by its email
	deleted_emails = {signup.email for signup in signups if signup.name in deleted_signups}
	for signup in signups:
		if signup.email not in deleted_emails:
			contacts.append((signup.email, None, signup.country, "Signup"))
	return contacts


def get_teams(signup_countries: dict[str, str]) -> tuple[dict[str, frappe._dict], set[str]]:
	"""Teams that are not deleted, and the signups of the deleted ones"""
	deleted = get_deleted_teams()
	with_active_site = set(
		frappe.get_all("Site", filters={"status": ("!=", "Archived")}, pluck="team", distinct=True)
	)

	teams: dict[str, frappe._dict] = {}
	deleted_signups: set[str] = set()
	for team in frappe.get_all("Team", fields=["name", "user", "country", "account_request"]):
		if team.name in deleted:
			deleted_signups.add(team.account_request)
			continue
		team.country = team.country or signup_countries.get(team.account_request)
		team.customer_type = "Active" if team.name in with_active_site else "Inactive"
		teams[team.name] = team
	return teams, deleted_signups


def get_deleted_teams() -> set[str]:
	"""Teams anonymized by a Team Deletion Request, under their old and new name"""
	requests = frappe.get_all("Team Deletion Request", filters={"status": "Deleted"}, fields=["name", "team"])
	return {request.team for request in requests} | {request.name for request in requests}


def get_team_emails() -> list[tuple[str, str]]:
	"""(team, email) for team members and the team's notification emails"""
	members = frappe.get_all(
		"Team Member", filters={"parenttype": "Team"}, fields=["parent", "user"], as_list=True
	)
	notification_emails = frappe.get_all(
		"Communication Info",
		filters={"parenttype": "Team", "channel": "Email"},
		fields=["parent", "value"],
		as_list=True,
	)
	return list(members) + list(notification_emails)
