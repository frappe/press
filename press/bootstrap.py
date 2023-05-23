# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
import os
import time
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete


ADMIN_EMAIL = ""
HOME_DIRECTORY = ""
CERTBOT_DIRECTORY = os.path.join(HOME_DIRECTORY, ".certbot")
WEBROOT_DIRECTORY = os.path.join(HOME_DIRECTORY, ".webroot")

# We've already configured Route 53 zone for this
# Don't change this unless you know what you're doing
ROOT_DOMAIN = "local.frappe.dev"
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

BENCH_PATH = ""
CLONE_DIRECTORY = os.path.join(BENCH_PATH, "clones")
BUILD_DIRECTORY = os.path.join(BENCH_PATH, "builds")

TELEGRAM_CHAT_ID = ""
TELEGRAM_BOT_TOKEN = ""

AGENT_REPOSITORY_OWNER = ""
GITHUB_ACCESS_TOKEN = ""

STRIPE_PUBLISHABLE_KEY = ""
STRIPE_SECRET_KEY = ""
NGROK_AUTH_TOKEN = ""

MAIL_SERVER = ""
MAIL_PORT = ""
MAIL_LOGIN = ""
MAIL_PASSWORD = ""


def prepare():
	complete_setup_wizard()
	settings = frappe.get_single("Press Settings")
	setup_certbot(settings)
	setup_root_domain(settings)
	setup_stripe(settings)

	setup_agent(settings)

	setup_proxy_server()
	setup_database_server()
	setup_server()

	setup_registry(settings)

	setup_logging(settings)
	setup_monitoring(settings)
	setup_tracing(settings)

	setup_apps()
	setup_teams()
	setup_plans()


def complete_setup_wizard():
	setup_complete(
		{
			"language": "English",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": "INR",
		}
	)


def setup_certbot(settings):
	settings.eff_registration_email = ADMIN_EMAIL
	settings.webroot_directory = WEBROOT_DIRECTORY
	settings.certbot_directory = CERTBOT_DIRECTORY
	settings.save()
	settings.reload()


def setup_root_domain(settings):
	if frappe.db.get_value("Root Domain", ROOT_DOMAIN):
		domain = frappe.get_doc("Root Domain", ROOT_DOMAIN)
	else:
		domain = frappe.get_doc(
			{
				"doctype": "Root Domain",
				"name": ROOT_DOMAIN,
				"default_cluster": "Default",
				"aws_access_key_id": AWS_ACCESS_KEY_ID,
				"aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
			}
		).insert()
	frappe.db.commit()
	while not frappe.db.exists(
		"TLS Certificate", {"wildcard": True, "domain": ROOT_DOMAIN, "status": "Active"}
	):
		print("Waiting for TLS certificate")
		time.sleep(1)
		frappe.db.commit()

	settings.domain = domain.name
	settings.cluster = domain.default_cluster
	settings.save()
	settings.reload()


def setup_stripe(settings):
	settings.stripe_publishable_key = STRIPE_PUBLISHABLE_KEY
	settings.stripe_secret_key = STRIPE_SECRET_KEY
	settings.ngrok_auth_token = NGROK_AUTH_TOKEN
	settings.save()
	settings.reload()


def setup_registry(settings):
	registry = frappe.get_doc(
		{
			"doctype": "Registry Server",
			"hostname": "registry",
			"ip": "10.0.4.101",
			"private_ip": "10.1.4.101",
		}
	).insert()

	settings.clone_directory = CLONE_DIRECTORY
	settings.build_directory = BUILD_DIRECTORY

	settings.docker_registry_url = registry.name
	settings.docker_registry_username = registry.registry_username
	settings.docker_registry_password = registry.get_password("registry_password")

	settings.save()
	settings.reload()


def setup_logging(settings):
	log = frappe.get_doc(
		{
			"doctype": "Log Server",
			"hostname": "log",
			"ip": "10.0.4.102",
			"private_ip": "10.1.4.102",
		}
	).insert()

	settings.log_server = log.name

	settings.save()
	settings.reload()


def setup_monitoring(settings):
	monitor = frappe.get_doc(
		{
			"doctype": "Monitor Server",
			"hostname": "monitor",
			"ip": "10.0.4.103",
			"private_ip": "10.1.4.103",
		}
	).insert()

	settings.monitor_server = monitor.name
	settings.monitor_token = frappe.generate_hash()
	settings.press_monitoring_password = frappe.generate_hash()

	frappe.get_doc(
		{
			"doctype": "Telegram Group",
			"name": "Alerts",
			"chat_id": TELEGRAM_CHAT_ID,
		}
	).insert()

	settings.telegram_alerts_chat_group = "Alerts"
	settings.telegram_bot_token = TELEGRAM_BOT_TOKEN

	settings.save()
	settings.reload()


def setup_tracing(settings):
	redirect_uri = f"https://trace.{ROOT_DOMAIN}/auth/sso/"
	oauth_client = frappe.get_doc(
		{
			"doctype": "OAuth Client",
			"app_name": "Sentry",
			"scopes": "all openid email",
			"default_redirect_uri": redirect_uri,
			"redirect_uris": redirect_uri,
			"skip_authorization": True,
		}
	).insert()

	frappe.get_doc(
		{
			"doctype": "Trace Server",
			"hostname": "trace",
			"ip": "10.0.4.105",
			"private_ip": "10.1.4.105",
			"sentry_admin_email": ADMIN_EMAIL,
			"sentry_admin_password": frappe.generate_hash(),
			"sentry_mail_server": MAIL_SERVER,
			"sentry_mail_port": MAIL_PORT,
			"sentry_mail_login": MAIL_LOGIN,
			"sentry_mail_password": MAIL_PASSWORD,
			"sentry_oauth_server_url": frappe.utils.get_url(),
			"sentry_oauth_client_id": oauth_client.client_id,
			"sentry_oauth_client_secret": oauth_client.client_secret,
		}
	).insert()


def setup_agent(settings):
	settings.agent_repository_owner = AGENT_REPOSITORY_OWNER
	settings.agent_github_access_token = GITHUB_ACCESS_TOKEN
	settings.github_access_token = GITHUB_ACCESS_TOKEN
	settings.save()
	settings.reload()


def setup_proxy_server():
	frappe.get_doc(
		{
			"doctype": "Proxy Server",
			"hostname": "n1",
			"ip": "10.0.1.101",
			"private_ip": "10.1.1.101",
		}
	).insert()


def setup_database_server():
	frappe.get_doc(
		{
			"doctype": "Database Server",
			"title": "First - Database",
			"hostname": "m1",
			"ip": "10.0.3.101",
			"private_ip": "10.1.3.101",
		}
	).insert()


def setup_server():
	frappe.get_doc(
		{
			"doctype": "Server",
			"title": "First - Application",
			"hostname": "f1",
			"ip": "10.0.2.101",
			"private_ip": "10.1.2.101",
			"proxy_server": f"n1.{ROOT_DOMAIN}",
			"database_server": f"m1.{ROOT_DOMAIN}",
		}
	).insert()


def setup():
	servers = [
		("Proxy Server", f"n1.{ROOT_DOMAIN}"),
		("Database Server", f"m1.{ROOT_DOMAIN}"),
		("Server", f"f1.{ROOT_DOMAIN}"),
		("Registry Server", f"registry.{ROOT_DOMAIN}"),
		("Log Server", f"log.{ROOT_DOMAIN}"),
		("Monitor Server", f"monitor.{ROOT_DOMAIN}"),
		("Trace Server", f"trace.{ROOT_DOMAIN}"),
	]
	for server_type, server in servers:
		frappe.get_doc(server_type, server).setup_server()


def setup_teams():
	from press.api.account import signup
	from press.press.doctype.team.team import Team

	signup("cloud@erpnext.com")
	request = frappe.get_all(
		"Account Request", ["*"], {"email": "cloud@erpnext.com"}, limit=1
	)[0]
	cloud = Team.create_new(request, "Frappe", "Cloud", "FrappeCloud@1", "India", False)

	signup("aditya@erpnext.com")
	request = frappe.get_all(
		"Account Request", ["*"], {"email": "aditya@erpnext.com"}, limit=1
	)[0]
	aditya = Team.create_new(request, "Aditya", "Hase", "AdityaHase@1", "India", False)

	cloud.append("team_members", {"user": aditya.name})
	cloud.save()


def setup_plans():
	plans = [("Free", 0), ("USD 10", 10), ("USD 25", 25)]
	for index, plan in enumerate(plans, 1):
		if frappe.db.exists("Plan", plan[0]):
			continue
		frappe.get_doc(
			{
				"doctype": "Plan",
				"name": plan[0],
				"document_type": "Site",
				"plan_title": plan[0],
				"price_usd": plan[1],
				"price_inr": plan[1] * 80,
				"cpu_time_per_day": index,
				"max_database_usage": 1024 * index,
				"max_storage_usage": 10240 * index,
				"roles": [
					{"role": "System Manager"},
					{"role": "Press Admin"},
					{"role": "Press Member"},
				],
			}
		).insert()


def setup_apps():
	app = frappe.get_doc(
		{"doctype": "App", "name": "frappe", "title": "Frappe Framework", "frappe": True}
	).insert()
	source = frappe.get_doc(
		{
			"doctype": "App Source",
			"app": app.name,
			"branch": "develop",
			"repository_url": "https://github.com/frappe/frappe",
			"public": True,
			"team": "Administrator",
			"versions": [{"version": "Nightly"}],
		}
	).insert()
	frappe.get_doc(
		{
			"doctype": "Release Group",
			"title": "Frappe",
			"version": "Nightly",
			"team": "Administrator",
			"apps": [{"app": app.name, "source": source.name}],
		}
	).insert()
