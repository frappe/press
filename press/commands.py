from __future__ import unicode_literals, absolute_import
import click

import frappe
from frappe.commands import pass_context, get_site


@click.command("ngrok-webhook")
@pass_context
def start_ngrok_and_set_webhook(context):
	from pyngrok import ngrok
	from press.api.billing import get_stripe

	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()

	port = frappe.conf.http_port or frappe.conf.webserver_port
	public_url = ngrok.connect(port=port, options={"host_header": site})
	print(f"Public URL: {public_url}")
	print("Inspect logs at http://localhost:4040")

	stripe = get_stripe()
	url = f"{public_url}/api/method/press.press.doctype.stripe_webhook_log.stripe_webhook_log.stripe_webhook_handler"
	stripe.WebhookEndpoint.modify(
		frappe.db.get_single_value("Press Settings", "stripe_webhook_endpoint_id"), url=url
	)
	print("Updated Stripe Webhook Endpoint")

	ngrok_process = ngrok.get_ngrok_process()
	try:
		# Block until CTRL-C or some other terminating event
		ngrok_process.proc.wait()
	except KeyboardInterrupt:
		print("Shutting down server...")
		frappe.destroy()
		ngrok.kill()


commands = [
	start_ngrok_and_set_webhook,
]
