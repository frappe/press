from frappe.model.document import Document


def action_key(document: Document) -> str:
	if document.doctype == "Site" and document.is_new():
		return "allow_site_creation"
	if document.doctype == "Server" and document.is_new():
		return "allow_server_creation"
	if document.doctype == "Release Group" and document.is_new():
		return "allow_bench_creation"
	if document.doctype == "Press Webhook":
		return "allow_webhook_configuration"
	return ""
