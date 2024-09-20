import frappe
from frappe.utils import flt
from frappe.utils.data import today

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

			partner = frappe.get_doc("Team", partner_request_doc.partner)
			customer_team = frappe.get_doc("Team", partner_request_doc.requested_by)
			customer_team.partner_email = partner.partner_email
			customer_team.partnership_date = frappe.utils.getdate(partner_request_doc.creation)
			team_members = [d.user for d in customer_team.team_members]
			if partner.user not in team_members:
				customer_team.append("team_members", {"user": partner.user})
			customer_team.save(ignore_permissions=True)

		frappe.db.commit()

	frappe.response.type = "redirect"
	frappe.response.location = f"/app/partner-approval-request/{partner_request_doc.name}"


@frappe.whitelist()
def get_partner_request_status(team):
	return frappe.db.get_value(
		"Partner Approval Request", {"requested_by": team}, "status"
	)


@frappe.whitelist()
def update_partnership_date(team, partnership_date):
	if team:
		team_doc = frappe.get_doc("Team", team)
		team_doc.partnership_date = partnership_date
		team_doc.save()


@frappe.whitelist()
def get_partner_details(partner_email):
	from press.utils.billing import get_frappe_io_connection, disabled_frappeio_auth

	if disabled_frappeio_auth():
		return frappe._dict(
			{
				"email": "",
				"partner_type": "",
				"company_name": "",
				"custom_ongoing_period_fc_invoice_contribution": "",
				"custom_ongoing_period_enterprise_invoice_contribution": "",
				"partner_name": "",
				"custom_number_of_certified_members": "",
			}
		)

	client = get_frappe_io_connection()
	data = client.get_doc(
		"Partner",
		filters={"email": partner_email, "enabled": 1},
		fields=[
			"email",
			"partner_type",
			"company_name",
			"custom_ongoing_period_fc_invoice_contribution",
			"custom_ongoing_period_enterprise_invoice_contribution",
			"partner_name",
			"custom_number_of_certified_members",
		],
	)
	if data:
		return data[0]
	else:
		frappe.throw("Partner Details not found")


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
	DISCOUNT_MAP = {"Entry": 0, "Bronze": 0.05, "Silver": 0.1, "Gold": 0.15}

	amt = frappe.utils.flt(amount)
	partner_doc = frappe.get_doc("Team", partner)
	credits_available = partner_doc.get_balance()
	partner_level, legacy_contract = partner_doc.get_partner_level()
	# no discount for partners on legacy contract
	# TODO: remove legacy contract check
	discount_percent = 0.0 if legacy_contract == 1 else DISCOUNT_MAP.get(partner_level)

	if credits_available < amt:
		frappe.throw(
			f"Insufficient Credits to transfer. Credits Available: {credits_available}"
		)

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
def get_partner_contribution(partner_email):
	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	month_end = frappe.utils.get_last_day(today())
	invoices = frappe.get_all(
		"Invoice",
		{"partner_email": partner_email, "due_date": month_end, "type": "Subscription"},
		["due_date", "customer_name", "total", "currency", "status"],
	)
	for d in invoices:
		if partner_currency != d.currency:
			if partner_currency == "USD":
				d.update({"partner_total": flt(d.total / 83, 2)})
			else:
				d.update({"partner_total": flt(d.total * 83)})
		else:
			d.update({"partner_total": d.total})
	return invoices


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
	return customers
