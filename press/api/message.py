import frappe
from frappe.rate_limiter import rate_limit
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=1200, seconds=60)
def confirmed_incident(server_title: str):
	response = Response()
	response.mimetype = "application/xml"
	response.data = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="man">Hi! Your dedicated server - {server_title} is facing some incidents and the hosted sites might be down.</Say>
    <Say voice="man">Our Engineers are working on it. </Say>
    <Say voice="man">Please check your email for incident updates.</Say>
    <Say voice="man">For any urgent assistance, please contact our support team.</Say>
    <Hangup/>
</Response>
"""
	return response
