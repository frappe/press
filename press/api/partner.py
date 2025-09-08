import frappe
from frappe.core.utils import find
from frappe.utils import flt
from frappe.utils.data import add_days, add_months, get_first_day, get_last_day, today

from press.utils import get_current_team


@frappe.whitelist()
def approve_partner_request(key):
	partner_request_doc = frappe.get_doc("Partner Approval Request", {"key": key})
	if partner_request_doc and partner_request_doc.status == "Pending":
		if partner_request_doc.approved_by_partner:
			partner_request_doc.approved_by_frappe = True
			partner_request_doc.status = "Approved"
			partner_request_doc.save(ignore_permissions=True)
			partner_request_doc.reload()

			partner_email = frappe.db.get_value("Team", partner_request_doc.partner, "partner_email")
			frappe.db.set_value(
				"Team",
				partner_request_doc.requested_by,
				{
					"partner_email": partner_email,
					"partnership_date": frappe.utils.getdate(partner_request_doc.creation),
				},
			)

		frappe.db.commit()

	frappe.response.type = "redirect"
	frappe.response.location = f"/app/partner-approval-request/{partner_request_doc.name}"


@frappe.whitelist()
def get_partner_request_status(team):
	return frappe.db.get_value("Partner Approval Request", {"requested_by": team}, "status")


@frappe.whitelist()
def update_partnership_date(team, partnership_date):
	if team:
		team_doc = frappe.get_doc("Team", team)
		team_doc.partnership_date = partnership_date
		team_doc.save()


@frappe.whitelist()
def update_website_info(website_info):
	from press.utils.billing import get_frappe_io_connection, is_frappe_auth_disabled

	if is_frappe_auth_disabled():
		return

	client = get_frappe_io_connection()
	try:
		website_info["doctype"] = "Partner"
		client.update(website_info)
	except Exception:
		frappe.log_error("Error updating website info")


@frappe.whitelist()
def get_partner_details(partner_email):
	from press.utils.billing import get_frappe_io_connection, is_frappe_auth_disabled

	if is_frappe_auth_disabled():
		return None

	client = get_frappe_io_connection()
	data = client.get_doc(
		"Partner",
		filters={"email": partner_email, "enabled": 1},
		fields=[
			"name",
			"email",
			"partner_type",
			"company_name",
			"partner_name",
			"custom_number_of_certified_members",
			"end_date",
			"partner_website",
			"introduction",
			"customers",
			"custom_process_maturity_level",
		],
	)
	if data:
		return data[0]
	frappe.throw("Partner Details not found")
	return None


@frappe.whitelist()
def get_partner_name(partner_email):
	return frappe.db.get_value(
		"Team",
		{"partner_email": partner_email, "enabled": 1, "erpnext_partner": 1},
		"billing_name",
	)


@frappe.whitelist()
def transfer_credits(amount, customer, partner):
	# partner discount map
	DISCOUNT_MAP = {"Entry": 0, "Emerging": 0.10, "Bronze": 0.10, "Silver": 0.15, "Gold": 0.20}

	amt = frappe.utils.flt(amount)
	partner_doc = frappe.get_doc("Team", partner)
	credits_available = partner_doc.get_balance()
	partner_level, certificates = partner_doc.get_partner_level()
	discount_percent = DISCOUNT_MAP.get(partner_level)

	if credits_available < amt:
		frappe.throw(f"Insufficient Credits to transfer. Credits Available: {credits_available}")

	customer_doc = frappe.get_doc("Team", customer)
	credits_to_transfer = amt
	amt -= amt * discount_percent
	if customer_doc.currency != partner_doc.currency:
		if partner_doc.currency == "USD":
			credits_to_transfer = credits_to_transfer * 83
		else:
			credits_to_transfer = credits_to_transfer / 83

	try:
		customer_doc.allocate_credit_amount(
			credits_to_transfer,
			"Transferred Credits",
			f"Transferred Credits from {partner_doc.name}",
		)
		partner_doc.allocate_credit_amount(
			amt * -1, "Transferred Credits", f"Transferred Credits to {customer_doc.name}"
		)
		frappe.db.commit()
		return amt
	except Exception:
		frappe.throw("Error in transferring credits")
		frappe.db.rollback()


@frappe.whitelist()
def get_partner_contribution_list(partner_email):
	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	month_end = frappe.utils.get_last_day(today())
	invoices = frappe.get_all(
		"Invoice",
		{"partner_email": partner_email, "due_date": month_end, "type": "Subscription"},
		["due_date", "customer_name", "total_before_discount", "currency", "status"],
	)

	for d in invoices:
		if partner_currency != d.currency:
			if partner_currency == "USD":
				d.update({"partner_total": flt(d.total_before_discount / 83, 2)})
			else:
				d.update({"partner_total": flt(d.total_before_discount * 83)})
		else:
			d.update({"partner_total": d.total_before_discount})
	return invoices


@frappe.whitelist()
def get_partner_mrr(partner_email):
	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	query = frappe.db.sql(
		f"""
			SELECT
				i.due_date,
				SUM(
					CASE
						WHEN '{partner_currency}' = i.currency THEN i.total_before_discount
						WHEN '{partner_currency}' = 'INR' AND i.currency = 'USD' THEN i.total_before_discount * 83
						WHEN '{partner_currency}' = 'USD' AND i.currency = 'INR' THEN i.total_before_discount / 83
						ELSE i.total_before_discount
					END
				) as total_amount
			FROM tabInvoice as i
			WHERE
				i.partner_email = '{partner_email}'
				AND i.type = 'Subscription'
				AND i.status = 'Paid'
			GROUP BY
				i.due_date
			ORDER BY i.due_date DESC
			LIMIT 12
		""",
		as_dict=True,
	)
	return [d for d in query]


@frappe.whitelist()
def get_dashboard_stats():
	team = get_current_team(get_doc=True)
	data = frappe.db.sql(
		f"""
			SELECT
				site.plan as plan,
				COUNT(site.name) as count
			FROM
				tabSite as site JOIN tabTeam as team ON site.team = team.name
			WHERE
				team.name = '{team.name}'
				AND site.status = 'Active'
			GROUP BY
				site.plan
		""",
		as_dict=True,
	)
	return [d for d in data]


@frappe.whitelist()
def get_lead_stats():
	team = get_current_team(get_doc=True)
	data = frappe.db.sql(
		f"""
			SELECT
				COUNT(name) as total,
				SUM(CASE WHEN status in ('Open', 'In Process') THEN 1 ELSE 0 END) as open,
				SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END) as won,
				SUM(CASE WHEN status = 'Lost' THEN 1 ELSE 0 END) as lost
			FROM
				`tabPartner Lead`
			WHERE
				partner_team = '{team.name}'
		""",
		as_dict=True,
	)
	return data[0] if data else {}


@frappe.whitelist()
def get_partner_invoices(due_date=None, status=None):
	partner_email = get_current_team(get_doc=True).partner_email

	filters = {
		"partner_email": partner_email,
		"type": "Subscription",
	}
	if due_date:
		filters["due_date"] = due_date
	if status:
		filters["status"] = status

	invoices = frappe.get_all(
		"Invoice",
		filters,
		["name", "due_date", "customer_name", "total_before_discount", "currency", "status"],
		order_by="due_date desc",
	)

	return invoices  # noqa: RET504


@frappe.whitelist()
def get_invoice_items(invoice):
	data = frappe.get_all(
		"Invoice Item",
		{"parent": invoice},
		["document_type", "document_name", "rate", "plan", "quantity", "amount"],
	)
	for d in data:
		team = frappe.db.get_value(d.document_type, d.document_name, "team")
		d["user"] = frappe.db.get_value("Team", team, "user")

	return data


@frappe.whitelist()
def get_current_month_partner_contribution(partner_email):
	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	month_end = frappe.utils.get_last_day(today())

	invoice = frappe.qb.DocType("Invoice")
	query = (
		frappe.qb.from_(invoice)
		.select(invoice.currency, invoice.total_before_discount)
		.where(
			(invoice.partner_email == partner_email)
			& (invoice.due_date == month_end)
			& (invoice.type == "Subscription")
			& (invoice.docstatus < 2)
		)
	)
	invoices = query.run(as_dict=True)
	total = 0
	for d in invoices:
		if partner_currency != d.currency:
			if partner_currency == "USD":
				total += flt(d.total_before_discount / 83, 2)
			else:
				total += flt(d.total_before_discount * 83, 2)
		else:
			total += d.total_before_discount

	return total


@frappe.whitelist()
def get_prev_month_partner_contribution(partner_email):
	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	first_day = get_first_day(today())
	two_weeks = add_days(first_day, 14)  # 15th day of the month
	last_month_end = get_last_day(add_months(today(), -1))

	invoice = frappe.qb.DocType("Invoice")
	query = (
		frappe.qb.from_(invoice)
		.select(invoice.currency, invoice.total_before_discount)
		.where(
			(invoice.partner_email == partner_email)
			& (invoice.due_date == last_month_end)
			& (invoice.type == "Subscription")
		)
	)

	if frappe.utils.getdate() >= first_day and frappe.utils.getdate() <= frappe.utils.getdate(two_weeks):
		# till 15th of the current month unpaid invoices can also be counted in contribution
		query = query.where((invoice.status).isin(["Unpaid", "Paid"]))
	else:
		query = query.where(invoice.status == "Paid")

	invoices = query.run(as_dict=True)

	total = 0
	for d in invoices:
		if partner_currency != d.currency:
			if partner_currency == "USD":
				total += flt(d.total_before_discount / 83, 2)
			else:
				total += flt(d.total_before_discount * 83, 2)
		else:
			total += d.total_before_discount
	return total


@frappe.whitelist()
def calculate_partner_tier(contribution, currency):
	partner_tier = frappe.qb.DocType("Partner Tier")
	query = frappe.qb.from_(partner_tier).select(partner_tier.name)
	if currency == "INR":
		query = query.where(partner_tier.target_in_inr <= contribution).orderby(
			partner_tier.target_in_inr, order=frappe.qb.desc
		)
	else:
		query = query.where(partner_tier.target_in_usd <= contribution).orderby(
			partner_tier.target_in_usd, order=frappe.qb.desc
		)

	tier = query.run(as_dict=True)
	return tier[0]


@frappe.whitelist()
def add_partner(referral_code: str):
	team = get_current_team(get_doc=True)
	partner = frappe.get_doc("Team", {"partner_referral_code": referral_code}).name
	if frappe.db.exists(
		"Partner Approval Request",
		{"partner": partner, "requested_by": team.name, "status": "Pending"},
	):
		return "Request already sent"

	doc = frappe.get_doc(
		{
			"doctype": "Partner Approval Request",
			"partner": partner,
			"requested_by": team.name,
			"status": "Pending",
			"send_mail": True,
		}
	)
	doc.insert(ignore_permissions=True)
	return None


@frappe.whitelist()
def validate_partner_code(code):
	partner = frappe.db.get_value(
		"Team",
		{"enabled": 1, "erpnext_partner": 1, "partner_referral_code": code},
		"billing_name",
	)
	if partner:
		return True, partner
	return False, None


@frappe.whitelist()
def get_partner_customers():
	team = get_current_team(get_doc=True)
	customers = frappe.get_all(
		"Team",
		{"enabled": 1, "erpnext_partner": 0, "partner_email": team.partner_email},
		["name", "user", "payment_mode", "billing_name", "currency"],
	)
	return customers  # noqa: RET504


@frappe.whitelist()
def get_partner_members(partner):
	from press.utils.billing import get_frappe_io_connection

	client = get_frappe_io_connection()
	return client.get_list(
		"LMS Certificate",
		filters={"partner": partner},
		fields=["member_name", "member_email", "course", "version"],
	)


@frappe.whitelist()
def get_partner_leads(status=None, engagement_stage=None):
	team = get_current_team()
	filters = {"partner_team": team}
	if status:
		filters["status"] = status
	if engagement_stage:
		filters["engagement_stage"] = engagement_stage
	return frappe.get_all(
		"Partner Lead",
		filters,
		["name", "organization_name", "lead_name", "status", "lead_source", "partner_team"],
	)


@frappe.whitelist()
def change_partner(lead_name, partner):
	team = get_current_team()
	doc = frappe.get_doc("Partner Lead", lead_name)
	if doc.partner_team != team:
		frappe.throw("You are not allowed to change the partner for this lead")

	doc.partner_team = partner
	doc.status = "Open"
	doc.save()


@frappe.whitelist()
def remove_partner():
	team = get_current_team(get_doc=True)
	if team.payment_mode == "Paid By Partner":
		frappe.throw(
			"Cannot remove partner from the team. Please change the payment mode to Prepaid Credits or Card"
		)

	partner_user = frappe.get_value(
		"Team", {"partner_email": team.partner_email, "erpnext_partner": 1}, "user"
	)
	member_to_remove = find(team.team_members, lambda x: x.user == partner_user)
	if member_to_remove:
		team.remove(member_to_remove)
	team.partner_email = ""
	team.save(ignore_permissions=True)


@frappe.whitelist()
def apply_for_certificate(member_name, certificate_type):
	team = get_current_team(get_doc=True)
	doc = frappe.new_doc("Partner Certificate Request")
	doc.update(
		{
			"partner_team": team.name,
			"partner_member_email": member_name,
			"course": certificate_type,
		}
	)
	doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_partner_teams():
	teams = frappe.get_all(
		"Team",
		{"enabled": 1, "erpnext_partner": 1},
		["partner_email", "billing_name", "country", "partner_tier", "name"],
	)
	return teams  # noqa: RET504


@frappe.whitelist()
def get_local_payment_setup():
	team = get_current_team()
	data = frappe._dict()
	data.mpesa_setup = frappe.db.get_value("Mpesa Setup", {"team": team}, "mpesa_setup_id") or None
	data.payment_gateway = frappe.db.get_value("Payment Gateway", {"team": team}, "name") or None
	return data


@frappe.whitelist()
def get_certificate_users():
	users = frappe.get_all("Partner Certificate", ["partner_member_email", "partner_member_name"])
	return users  # noqa: RET504


@frappe.whitelist()
def get_lead_details(lead_id):
	return frappe.get_doc("Partner Lead", lead_id).as_dict()


@frappe.whitelist()
def update_lead_details(lead_name, lead_details):
	lead_details = frappe._dict(lead_details)
	doc = frappe.get_doc("Partner Lead", lead_name)
	doc.update(
		{
			"organization_name": lead_details.organization_name,
			"status": lead_details.status,
			"full_name": lead_details.full_name,
			"domain": lead_details.domain,
			"email": lead_details.email,
			"contact_no": lead_details.contact_no,
			"state": lead_details.state,
			"country": lead_details.country,
			"plan_proposed": lead_details.plan_proposed,
			"requirement": lead_details.requirement,
			"probability": lead_details.probability,
		}
	)
	doc.save(ignore_permissions=True)
	doc.reload()


@frappe.whitelist()
def update_lead_status(lead_name, status, **kwargs):
	status_dict = {"status": status}
	if status == "In Process":
		status_dict.update(
			{
				"engagement_stage": kwargs.get("engagement_stage"),
			}
		)
		if kwargs.get("proposed_plan") and kwargs.get("expected_close_date"):
			status_dict.update(
				{
					"plan_proposed": kwargs.get("proposed_plan"),
					"estimated_closure_date": kwargs.get("expected_close_date"),
				}
			)
	elif status == "Won":
		status_dict.update(
			{
				"conversion_date": kwargs.get("conversion_date"),
				"hosting": kwargs.get("hosting"),
				"site_url": kwargs.get("site_url"),
			}
		)
	elif status == "Lost":
		status_dict.update(
			{
				"lost_reason": kwargs.get("lost_reason"),
				"lost_reason_specify": kwargs.get("other_reason"),
			}
		)

	frappe.db.set_value("Partner Lead", lead_name, status_dict)


@frappe.whitelist()
def fetch_followup_details(id, lead):
	return frappe.get_all(
		"Lead Followup",
		{"parent": lead, "name": id, "parenttype": "Partner Lead"},
		[
			"name",
			"date",
			"communication_type",
			"followup_by",
			"spoke_to",
			"designation",
			"discussion",
			"no_show",
		],
	)


@frappe.whitelist()
def check_certificate_exists(email, type):
	return frappe.db.count("Partner Certificate", {"partner_member_email": email})


@frappe.whitelist()
def update_followup_details(id, lead, followup_details):
	followup_details = frappe._dict(followup_details)
	if id:
		doc = frappe.get_doc("Lead Followup", id)
		doc.update(
			{
				"date": frappe.utils.getdate(followup_details.followup_date),
				"communication_type": followup_details.communication_type,
				"followup_by": followup_details.followup_by,
				"spoke_to": followup_details.spoke_to,
				"designation": followup_details.designation,
				"discussion": followup_details.discussion,
				"no_show": followup_details.no_show,
			}
		)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.new_doc("Lead Followup")
		doc.update(
			{
				"parent": lead,
				"parenttype": "Partner Lead",
				"parentfield": "followup",
				"date": frappe.utils.getdate(followup_details.followup_date),
				"communication_type": followup_details.communication_type,
				"followup_by": followup_details.followup_by,
				"spoke_to": followup_details.spoke_to,
				"designation": followup_details.designation,
				"discussion": followup_details.discussion,
				"no_show": followup_details.no_show,
			}
		)
		doc.insert(ignore_permissions=True)
	doc.reload()


@frappe.whitelist()
def add_new_lead(lead_details):
	lead_details = frappe._dict(lead_details)
	doc = frappe.new_doc("Partner Lead")
	doc.update(
		{
			"organization_name": lead_details.organization_name,
			"full_name": lead_details.full_name,
			"domain": lead_details.domain,
			"email": lead_details.email,
			"lead_name": lead_details.lead_name,
			"contact_no": lead_details.contact_no,
			"state": lead_details.state,
			"country": lead_details.country,
			"requirement": lead_details.requirement,
			"partner_team": get_current_team(),
			"lead_source": lead_details.lead_source or "Partner Owned",
			"lead_type": lead_details.lead_type,
			"status": "Open",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.reload()


@frappe.whitelist()
def delete_followup(id, lead_name):
	frappe.delete_doc("Lead Followup", id)
