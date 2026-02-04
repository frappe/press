import json

import frappe
from frappe.core.utils import find
from frappe.desk.form.load import get_docinfo
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum
from frappe.utils import flt
from frappe.utils.data import add_days, add_months, get_first_day, get_last_day, today
from frappe.utils.user import is_system_user

from press.guards import role_guard
from press.utils import get_current_team


def is_lead_team(lead):
	team = get_current_team()
	if (frappe.db.get_value("Partner Lead", lead, "partner_team") == team) or is_system_user():
		return True
	return False


@frappe.whitelist()
@role_guard.api("partner")
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
@role_guard.api("partner")
def get_partner_request_status(team):
	return frappe.db.get_value("Partner Approval Request", {"requested_by": team}, "status")


@frappe.whitelist()
@role_guard.api("partner")
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
@role_guard.api("partner")
def get_partner_details(partner_email):
	from press.utils.billing import get_frappe_io_connection, is_frappe_auth_disabled

	if is_frappe_auth_disabled():
		return None

	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None

	client = get_frappe_io_connection()
	data = client.get_doc(
		"Partner",
		filters={"email": partner_email},
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
			"phone_number",
			"address",
			"custom_foundation_date",
			"custom_team_size",
			"custom_successful_projects_count",
			"custom_journey_blog_link",
		],
	)
	if data:
		return data[0]
	frappe.throw("Partner Details not found")
	return None


@frappe.whitelist()
@role_guard.api("partner")
def send_link_certificate_request(user_email, certificate_type):
	if not frappe.db.exists(
		"Partner Certificate", {"partner_member_email": user_email, "course": certificate_type}
	):
		frappe.throw(f"No certificate found for the {user_email} with given course")

	team = get_current_team(get_doc=True)

	frappe.get_doc(
		{
			"doctype": "Certificate Link Request",
			"partner_team": team.name,
			"user_email": user_email,
			"course": certificate_type,
		}
	).insert()


@frappe.whitelist()
@role_guard.api("partner")
def approve_certificate_link_request(key):
	cert_req_doc = frappe.get_doc("Certificate Link Request", {"key": key})
	cert_req_doc.status = "Approved"
	cert_req_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.response.type = "redirect"
	frappe.response.location = "/dashboard/partners/certificates"


@frappe.whitelist()
@role_guard.api("partner")
def get_resource_url():
	return frappe.db.get_value("Press Settings", "Press Settings", "drive_resource_link")


@frappe.whitelist()
@role_guard.api("partner")
def get_partner_name(partner_email):
	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None
	return frappe.db.get_value(
		"Team",
		{"partner_email": partner_email, "enabled": 1, "erpnext_partner": 1},
		"billing_name",
	)


@frappe.whitelist()
@role_guard.api("partner")
def transfer_credits(amount, customer):
	# partner discount map
	DISCOUNT_MAP = {"Entry": 0.10, "Emerging": 0.10, "Bronze": 0.15, "Silver": 0.20, "Gold": 0.25}

	partner = get_current_team(get_doc=True)
	if not partner.erpnext_partner and partner.partner_status != "Active":
		frappe.throw("Only Partner team can transfer credits.")

	amt = frappe.utils.flt(amount)
	partner_doc = frappe.get_doc("Team", partner)
	credits_available = partner_doc.get_balance()
	partner_level = partner_doc.get_partner_level()
	discount_percent = DISCOUNT_MAP.get(partner_level[0]) if partner_level else 0

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
@role_guard.api("partner")
def get_partner_contribution_list(partner_email):
	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None

	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)
	month_start = frappe.utils.get_first_day(today())
	month_end = frappe.utils.get_last_day(today())
	invoices = frappe.get_all(
		"Invoice",
		{
			"partner_email": partner_email,
			"due_date": ("between", [month_start, month_end]),
			"type": "Subscription",
		},
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
@role_guard.api("partner")
def get_partner_mrr(partner_email):
	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None

	partner_currency = frappe.db.get_value(
		"Team", {"erpnext_partner": 1, "partner_email": partner_email}, "currency"
	)

	Invoice = frappe.qb.DocType("Invoice")
	case_stmt = Case()

	if partner_currency == "INR":
		case_stmt.when(Invoice.currency == "USD", Invoice.total_before_discount * 83)
		case_stmt.when(Invoice.currency == "INR", Invoice.total_before_discount)
	elif partner_currency == "USD":
		case_stmt.when(Invoice.currency == "INR", Invoice.total_before_discount / 83)
		case_stmt.when(Invoice.currency == "USD", Invoice.total_before_discount)

	case_stmt.else_(Invoice.total_before_discount)

	query = (
		frappe.qb.from_(Invoice)
		.select(Invoice.due_date, case_stmt.as_("total_amount"))
		.where(
			(Invoice.partner_email == partner_email)
			& (Invoice.type == "Subscription")
			& (Invoice.status == "Paid")
		)
		.groupby(Invoice.due_date)
		.orderby(Invoice.due_date, order=frappe.qb.desc)
		.limit(12)
	)
	result = query.run(as_dict=True)
	return [d for d in result]


@frappe.whitelist()
@role_guard.api("partner")
def get_dashboard_stats():
	team = get_current_team(get_doc=True)
	Site = frappe.qb.DocType("Site")
	Team = frappe.qb.DocType("Team")
	query = (
		frappe.qb.from_(Site)
		.select((Site.plan).as_("plan"), Count(Site.name).as_("count"))
		.join(Team)
		.on(Site.team == Team.name)
		.where((Team.name == team.name) & (Site.status == "Active"))
		.groupby(Site.plan)
	)
	data = query.run(as_dict=True)
	return [d for d in data]


@frappe.whitelist()
@role_guard.api("partner")
def get_lead_stats():
	team = get_current_team(get_doc=True)
	Lead = frappe.qb.DocType("Partner Lead")
	query = (
		frappe.qb.from_(Lead)
		.select(
			Count(Lead.name).as_("total"),
			Sum(Case().when(Lead.status.isin(["Open", "In Process"]), 1).else_(0)).as_("open"),
			Sum(Case().when(Lead.status == "Won", 1).else_(0)).as_("won"),
			Sum(Case().when(Lead.status == "Lost", 1).else_(0)).as_("lost"),
		)
		.where(Lead.partner_team == team.name)
	)
	data = query.run(as_dict=True)
	return data[0] if data else {}


def get_user_by_name(email):
	return frappe.get_cached_value("User", email, "full_name")


@frappe.whitelist()
@role_guard.api("partner")
def get_lead_activities(name):  # noqa: C901
	if not is_lead_team(name):
		return None

	doc = frappe.db.get_values("Partner Lead", name, ["creation", "owner"])[0]
	get_docinfo("", "Partner Lead", name)
	res = frappe.response["docinfo"]
	doc_meta = frappe.get_meta("Partner Lead")
	fields = {field.fieldname: {"label": field.label, "options": field.options} for field in doc_meta.fields}

	activities = []
	activities.append(
		{"activity_type": "creation", "creation": doc[0], "owner": doc[1], "data": "created this lead"}
	)

	res.versions.reverse()

	for version in res.versions:
		data = json.loads(version.data)
		if not data.get("changed"):
			continue

		if change := data.get("changed")[0]:
			field = fields.get(change[0], None)
			if not field or (not change[1] and not change[2]):
				continue

			field_label = field.get("label") or change[0]
			field_option = field.get("options") or None

			activity_type = "changed"
			data = {
				"field": change[0],
				"field_label": field_label,
				"old_value": change[1],
				"new_value": change[2],
			}

			if not change[1] and change[2]:
				activity_type = "added"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[2],
				}
			elif change[1] and not change[2]:
				activity_type = "removed"
				data = {
					"field": change[0],
					"field_label": field_label,
					"value": change[1],
				}

		activity = {
			"activity_type": activity_type,
			"creation": version.creation,
			"owner": get_user_by_name(version.owner),
			"data": data,
			"options": field_option,
		}
		activities.append(activity)

	for comment in res.comments:
		activity = {
			"name": comment.name,
			"activity_type": "comment",
			"creation": comment.creation,
			"owner": get_user_by_name(comment.owner),
			"content": comment.content,
			# "attachments": get_attachments("Comment", comment.name),
		}
		activities.append(activity)

	activities.sort(key=lambda x: x.get("creation"), reverse=False)
	activities = handle_multiple_versions(activities)

	return activities  # noqa: RET504


def handle_multiple_versions(versions):  # noqa: C901
	# print(versions)
	activities = []
	grouped_versions = []
	old_version = None
	for version in versions:
		is_version = version["activity_type"] in ["changed", "added", "removed"]
		if not is_version:
			activities.append(version)
		if not old_version:
			old_version = version
			if is_version:
				grouped_versions.append(version)
			continue
		if is_version and old_version.get("owner") and version["owner"] == old_version["owner"]:
			grouped_versions.append(version)
		else:
			if grouped_versions:
				activities.append(parse_grouped_versions(grouped_versions))
			grouped_versions = []
			if is_version:
				grouped_versions.append(version)
		old_version = version
		if version == versions[-1] and grouped_versions:
			activities.append(parse_grouped_versions(grouped_versions))

	return activities


def parse_grouped_versions(versions):
	version = versions[0]
	if len(versions) == 1:
		return version
	other_versions = versions[1:]
	version["other_versions"] = other_versions
	return version


@frappe.whitelist()
@role_guard.api("partner")
def get_certification_requests():
	from frappe.frappeclient import FrappeClient

	team = get_current_team()
	cert_requests = frappe.get_all(
		"Partner Certificate Request",
		{"partner_team": team},
		["partner_member_name", "partner_member_email", "course"],
	)

	for d in cert_requests:
		d["course"] = "erpnext" if d["course"] == "erpnext-distribution" else "framework"
		d["email"] = d["partner_member_email"]

	press_settings = frappe.get_cached_doc("Press Settings")
	school_url = press_settings.school_url
	api_key = press_settings.school_api_key
	api_secret = press_settings.get_password("school_api_secret")

	client = FrappeClient(school_url, api_key=api_key, api_secret=api_secret)
	res = client.get_api("get-certificate-request-status", {"data": json.dumps(cert_requests)})

	if res:
		for d in res:
			d["course"] = "ERPNext" if d["course"] == "erpnext" else "Framework"

	return res


@frappe.whitelist()
@role_guard.api("partner")
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
@role_guard.api("partner")
def get_invoice_items(invoice):
	team = get_current_team()
	if team != frappe.db.get_value("Invoice", invoice, "team"):
		return None
	data = frappe.get_all(
		"Invoice Item",
		{"parent": invoice},
		["document_type", "document_name", "rate", "plan", "quantity", "amount"],
	)
	for d in data:
		team = frappe.db.get_value(d.document_type, d.document_name, "team")
		values = frappe.db.get_value("Team", team, ["user", "billing_name"], as_dict=True)
		d["user"] = values.user
		d["billing_name"] = values.billing_name

	return data


@frappe.whitelist()
@role_guard.api("partner")
def get_current_month_partner_contribution(partner_email):
	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None
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
@role_guard.api("partner")
def get_prev_month_partner_contribution(partner_email):
	team = get_current_team(get_doc=True)
	if team.partner_email != partner_email:
		return None
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
@role_guard.api("partner")
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
@role_guard.api("partner")
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
@role_guard.api("partner")
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
@role_guard.api("partner")
def get_partner_customers():
	team = get_current_team(get_doc=True)
	customers = frappe.get_all(
		"Team",
		{"enabled": 1, "erpnext_partner": 0, "partner_email": team.partner_email},
		["name", "user", "payment_mode", "billing_name", "currency"],
	)
	return customers  # noqa: RET504


@frappe.whitelist()
@role_guard.api("partner")
def get_partner_members(partner):
	from press.utils.billing import get_frappe_io_connection

	client = get_frappe_io_connection()
	return client.get_list(
		"LMS Certificate",
		filters={"partner": partner},
		fields=["member_name", "member_email", "course", "version"],
	)


@frappe.whitelist()
@role_guard.api("partner")
def get_partner_leads(lead_name=None, status=None, engagement_stage=None, source=None):
	team = get_current_team()
	filters = {"partner_team": team}
	if lead_name:
		filters["lead_name"] = ("like", f"%{lead_name}%")
	if status:
		filters["status"] = status
	if engagement_stage:
		filters["engagement_stage"] = engagement_stage
	if source:
		filters["lead_source"] = source
	return frappe.get_all(
		"Partner Lead",
		filters,
		["name", "organization_name", "lead_name", "status", "lead_source", "partner_team"],
	)


@frappe.whitelist()
@role_guard.api("partner")
def change_partner(lead_name, partner):
	doc = frappe.get_doc("Partner Lead", lead_name)
	if not is_lead_team(lead_name):
		frappe.throw("You are not allowed to change the partner for this lead")

	doc.partner_team = partner
	doc.status = "Open"
	doc.save()


@frappe.whitelist()
@role_guard.api("partner")
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
@role_guard.api("partner")
def apply_for_certificate(member_name, certificate_type):
	team = get_current_team(get_doc=True)
	if not team.erpnext_partner and team.partner_status != "Active":
		frappe.throw("Only Active Partner team can apply for certificates.")

	if frappe.db.exists(
		"Partner Certificate Request", {"partner_member_email": member_name, "course": certificate_type}
	):
		frappe.throw("A certificate request already exists for this team member and course.")

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
@role_guard.api("partner")
def get_partner_teams(company=None, email=None, country=None, tier=None, active_only=False):
	if not is_system_user(frappe.session.user):
		frappe.throw("Only system users can access partner teams.")

	filters = {"enabled": 1, "erpnext_partner": 1}
	if company:
		filters["company_name"] = ("like", f"%{company}%")
	if email:
		filters["partner_email"] = ("like", f"%{email}%")
	if country:
		filters["country"] = ("like", f"%{country}%")
	if tier:
		filters["partner_tier"] = tier
	if active_only:
		filters["partner_status"] = "Active"

	teams = frappe.get_all(
		"Team",
		filters,
		["partner_email", "company_name", "country", "partner_tier", "name"],
	)
	return teams  # noqa: RET504


@frappe.whitelist()
@role_guard.api("partner")
def get_local_payment_setup():
	team = get_current_team()
	data = frappe._dict()
	data.mpesa_setup = frappe.db.get_value("Mpesa Setup", {"team": team}, "mpesa_setup_id") or None
	data.payment_gateway = frappe.db.get_value("Payment Gateway", {"team": team}, "name") or None
	return data


@frappe.whitelist()
@role_guard.api("partner")
def get_lead_details(lead_id):
	if not is_lead_team(lead_id):
		return None
	return frappe.get_doc("Partner Lead", lead_id).as_dict()


@frappe.whitelist()
@role_guard.api("partner")
def update_lead_details(lead_name, lead_details):
	lead_details = frappe._dict(lead_details)
	doc = frappe.get_doc("Partner Lead", lead_name)
	if not is_lead_team(lead_name):
		frappe.throw("You are not allowed to update this lead")
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
			"engagement_stage": lead_details.engagement_stage,
		}
	)
	doc.save(ignore_permissions=True)
	doc.reload()


@frappe.whitelist()
@role_guard.api("partner")
def update_lead_status(lead_name, status, **kwargs):
	if not is_lead_team(lead_name):
		frappe.throw("You are not allowed to update this lead")

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
@role_guard.api("partner")
def fetch_followup_details(id, lead):
	if not is_lead_team(lead):
		return None

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
@role_guard.api("partner")
def check_certificate_exists(email, type):
	return frappe.db.count("Partner Certificate", {"partner_member_email": email, "course": type})


@frappe.whitelist()
def get_fc_plans():
	site_plans = frappe.get_all(
		"Site Plan", {"enabled": 1, "document_type": "Site", "price_inr": (">", 0)}, pluck="name"
	)
	return [*site_plans, "Dedicated Server", "Managed Press"]


@frappe.whitelist()
@role_guard.api("partner")
def update_followup_details(id, lead, followup_details):
	if not is_lead_team(lead):
		frappe.throw("You are not allowed to update this followup")

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
@role_guard.api("partner")
def add_new_lead(lead_details):
	lead_details = frappe._dict(lead_details)
	team = get_current_team(get_doc=True)
	if (not team.erpnext_partner and team.partner_status != "Active") or not is_system_user():
		frappe.throw("Only Active Partner team can add new leads.")

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
@role_guard.api("partner")
def can_apply_for_certificate():
	from press.utils.billing import get_frappe_io_connection

	team = get_current_team(get_doc=True)
	client = get_frappe_io_connection()
	response = client.get_api("check_free_certificate", {"partner_email": team.partner_email})

	return response  # noqa: RET504


@frappe.whitelist()
@role_guard.api("partner")
def delete_followup(id):
	frappe.delete_doc("Lead Followup", id)
