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

	# Set ngrok auth token
	auth_token = frappe.db.get_single_value("Press Settings", "ngrok_auth_token")

	if auth_token:
		ngrok.set_auth_token(auth_token)

	port = frappe.conf.http_port or frappe.conf.webserver_port
	tunnel = ngrok.connect(port, host_header=site)
	public_url = tunnel.public_url
	print()
	print(f"{public_url} -> http://{site}:{port}")
	print(f"Inspect logs at {tunnel.api_url}")

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
