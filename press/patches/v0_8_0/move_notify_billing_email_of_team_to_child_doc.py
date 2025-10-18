import frappe


def sanitize_emails(email_str: str):
	if not email_str:
		return []

	# Check if multiple emails are separated by comma or semicolon
	if "," in email_str:
		emails = [email.strip() for email in email_str.split(",")]
	elif ";" in email_str:
		emails = [email.strip() for email in email_str.split(";")]
	else:
		emails = [email_str.strip()]

	return [email for email in emails if email]


def execute():
	Team = frappe.qb.DocType("Team")

	# First test if the columns exist
	if not frappe.db.has_column("Team", "notify_email") or not frappe.db.has_column("Team", "billing_email"):
		print("notify_email or billing_email column does not exist in Team table")
		print("Skipping patch for moving notify and billing email to Communication Info child table")
		return

	query = (
		frappe.qb.from_(Team)
		.select(Team.name, Team.notify_email, Team.billing_email)
		.where(
			(Team.notify_email.isnotnull() & Team.user != Team.notify_email)
			| (Team.billing_email.isnotnull() & Team.user != Team.billing_email)
		)
	)
	results = query.run(as_dict=True)

	values = []
	for row in results:
		team_name = row.name
		mails = sanitize_emails(row.notify_email)
		for mail in mails:
			values.append(
				[
					frappe.utils.generate_hash(length=12),
					team_name,
					"Team",
					"communication_infos",
					"Email",
					"General",
					mail,
				]
			)
		mails = sanitize_emails(row.billing_email)
		for mail in mails:
			values.append(
				[
					frappe.utils.generate_hash(length=12),
					team_name,
					"Team",
					"communication_infos",
					"Email",
					"Billing",
					mail,
				]
			)

	frappe.db.bulk_insert(
		"Communication Info",
		["name", "parent", "parenttype", "parentfield", "channel", "type", "value"],
		values,
	)
