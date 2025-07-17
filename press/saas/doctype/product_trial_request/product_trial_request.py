# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import urllib
import urllib.parse
from contextlib import suppress
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from frappe.utils.data import add_to_date, now_datetime
from frappe.utils.telemetry import init_telemetry

from press.api.client import dashboard_whitelist
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site
	from press.saas.doctype.product_trial.product_trial import ProductTrial


class ProductTrialRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_request: DF.Link | None
		agent_job: DF.Link | None
		cluster: DF.Link | None
		domain: DF.Data | None
		is_standby_site: DF.Check
		product_trial: DF.Link | None
		site: DF.Link | None
		site_creation_completed_on: DF.Datetime | None
		site_creation_started_on: DF.Datetime | None
		status: DF.Literal[
			"Pending",
			"Wait for Site",
			"Prefilling Setup Wizard",
			"Adding Domain",
			"Site Created",
			"Error",
			"Expired",
		]
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ("site", "status", "product_trial", "domain")

	agent_job_step_to_frontend_step = {  # noqa: RUF012
		"New Site": {
			"New Site": "Building Site",
			"Install Apps": "Installing Apps",
			"Update Site Configuration": "Updating Configuration",
			"Enable Scheduler": "Finalizing Site",
			"Bench Setup Nginx": "Finalizing Site",
			"Reload Nginx": "Just a moment",
		},
		"Rename Site": {
			"Enable Maintenance Mode": "Starting",
			"Wait for Enqueued Jobs": "Starting",
			"Update Site Configuration": "Preparing Site",
			"Rename Site": "Preparing Site",
			"Bench Setup NGINX": "Preparing Site",
			"Reload NGINX": "Finalizing Site",
			"Disable Maintenance Mode": "Finalizing Site",
			"Enable Scheduler": "Just a moment",
		},
	}

	def get_email(self):
		return frappe.db.get_value("Team", self.team, "user")

	@redis_cache(ttl=2 * 60)
	def is_first_trial_request(self) -> bool:
		return (
			frappe.db.count(
				"Product Trial Request",
				filters={
					"account_request": self.account_request,
					"name": ("!=", self.name),
					"status": ("not in", ["Expired", "Error", "Pending"]),
				},
			)
			< 1
		)

	def capture_posthog_event(self, event_name):
		if not self.is_first_trial_request():
			# Only capture events for the first trial request
			return

		init_telemetry()
		ph = getattr(frappe.local, "posthog", None)
		with suppress(Exception):
			ph and ph.capture(
				distinct_id=self.account_request,
				event=f"fc_product_trial_{event_name}",
				properties={
					"product_trial": True,
					"product_trial_request_id": self.name,
					"product_trial_id": self.product_trial,
					"email": self.get_email(),
				},
			)

	def set_posthog_alias(self, new_alias: str):
		if not self.is_first_trial_request():
			# Only set alias for the first trial request
			return

		init_telemetry()
		ph = getattr(frappe.local, "posthog", None)
		with suppress(Exception):
			ph and ph.alias(previous_id=self.account_request, distinct_id=new_alias)

	def after_insert(self):
		self.capture_posthog_event("product_trial_request_created")

	def on_update(self):
		if self.has_value_changed("site") and self.site:
			self.set_posthog_alias(self.site)

		if self.has_value_changed("status"):
			match self.status:
				case "Error":
					self.capture_posthog_event("product_trial_request_failed")
				case "Wait for Site":
					self.capture_posthog_event("product_trial_request_initiated_site_creation")
				case "Prefilling Setup Wizard":
					self.capture_posthog_event("product_trial_request_started_setup_wizard_prefilled")
				case "Site Created":
					self.capture_posthog_event("product_trial_request_site_created")

					# this is to create a webhook record in the site
					# so that the user records can be synced with press
					site: Site = frappe.get_doc("Site", self.site)
					site.create_sync_user_webhook()

	@frappe.whitelist()
	def get_setup_wizard_payload(self):
		import json

		try:
			team_details = frappe.db.get_value(
				"Team", self.team, ["name", "user", "country", "currency"], as_dict=True
			)
			team_user = frappe.db.get_value(
				"User", team_details.user, ["first_name", "last_name", "full_name", "email"], as_dict=True
			)

			if self.account_request:
				account_request_geo_data = frappe.db.get_value(
					"Account Request", self.account_request, "geo_location"
				)
			else:
				account_request_geo_data = frappe.db.get_value(
					"Account Request", {"email": team_user.email}, "geo_location"
				)

			timezone = frappe.parse_json(account_request_geo_data or {}).get("timezone", "Asia/Kolkata")

			return json.dumps(
				{
					"email": team_user.email,
					"first_name": team_user.first_name,
					"last_name": team_user.last_name,
					"full_name": team_user.full_name,
				}
			), json.dumps(
				{
					"country": team_details.country,
					"time_zone": timezone,
					"language": "en",
					"currency": team_details.currency,
					# setup wizard will override currency anyway
					# but adding this since ERPNext will throw an error otherwise
				}
			)
		except Exception as e:
			log_error(
				title="Product Trial Request Setup Wizard Payload Generation Error",
				data=e,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
			frappe.throw(f"Failed to generate payload for Setup Wizard: {e}")

	@dashboard_whitelist()
	def create_site(self, subdomain: str, domain: str):
		"""
		Trigger the site creation process for the product trial request.
		Args:
			subdomain (str): The subdomain for the new site.
			domain (str): The domain for the new site.
		"""
		if self.status != "Pending":
			return

		if not subdomain:
			frappe.throw("Subdomain is required to create a site.")

		try:
			product: ProductTrial = frappe.get_doc("Product Trial", self.product_trial)
			self.status = "Wait for Site"
			self.site_creation_started_on = now_datetime()
			self.domain = f"{subdomain}.{domain}"
			cluster = frappe.db.get_value("Root Domain", domain, "default_cluster")
			self.cluster = cluster
			site, agent_job_name, is_standby_site = product.setup_trial_site(
				subdomain=subdomain,
				domain=domain,
				team=self.team,
				cluster=cluster,
				account_request=self.account_request,
			)
			self.is_standby_site = is_standby_site
			self.agent_job = agent_job_name
			self.site = site.name
			self.save()

			if is_standby_site:
				self.prefill_setup_wizard_data()

			user_mail = frappe.db.get_value("Team", self.team, "user")
			frappe.get_doc(
				{
					"doctype": "Site User",
					"site": site.name,
					"user": user_mail,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
		except frappe.exceptions.ValidationError:
			raise
		except Exception as e:
			log_error(
				title="Product Trial Request Site Creation Error",
				data=e,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
			self.status = "Error"
			self.save()

	@dashboard_whitelist()
	def get_progress(self, current_progress=None):  # noqa: C901
		current_progress = current_progress or 10
		if self.agent_job:
			filters = {"name": self.agent_job, "site": self.site}
		else:
			filters = {"site": self.site, "job_type": ["in", ["New Site", "Rename Site"]]}
		job_name, status, job_type = frappe.db.get_value(
			"Agent Job",
			filters,
			["name", "status", "job_type"],
		)
		if status == "Success":
			if self.status == "Site Created":
				return {"progress": 100}
			if self.status == "Adding Domain":
				return {"progress": 90, "current_step": self.status}
			return {"progress": 80, "current_step": self.status}

		if status == "Running":
			steps = frappe.db.get_all(
				"Agent Job Step",
				filters={"agent_job": job_name},
				fields=["step_name", "status"],
				order_by="creation asc",
			)
			done = [s for s in steps if s.status in ("Success", "Skipped", "Failure")]
			steps_count = len(steps)
			steps_count += 1
			progress = (len(done) / steps_count) * 100
			progress = max(progress, current_progress)
			current_running_step = ""
			for step in steps:
				if step.status == "Running":
					current_running_step = self.agent_job_step_to_frontend_step.get(job_type, {}).get(
						step.step_name, step.step_name
					)
					break
			return {"progress": progress + 0.1, "current_step": current_running_step}

		if self.status == "Error":
			return {"progress": current_progress, "error": True}

		# If agent job is undelivered, pending
		return {"progress": current_progress + 0.1}

	def prefill_setup_wizard_data(self):
		if self.status == "Prefilling Setup Wizard":
			return

		site: Site = frappe.get_doc("Site", self.site)
		try:
			user_payload, system_settings_payload = self.get_setup_wizard_payload()
			site.prefill_setup_wizard(system_settings_payload, user_payload)
			if self.site != self.domain:
				self.status = "Prefilling Setup Wizard"
				self.save()
		except Exception as e:
			log_error(
				title="Product Trial Request Prefill Setup Wizard Error",
				data=e,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	@dashboard_whitelist()
	def get_login_sid(self):
		site: Site = frappe.get_doc("Site", self.site)
		redirect_to_after_login = frappe.db.get_value(
			"Product Trial",
			self.product_trial,
			"redirect_to_after_login",
		)
		if site.additional_system_user_created and site.setup_wizard_complete:
			# go to setup wizard as admin only
			# they'll log in as user after setup wizard
			email = frappe.db.get_value("Team", self.team, "user")
			sid = site.get_login_sid(user=email)
			return f"https://{self.domain or self.site}{redirect_to_after_login}?sid={sid}"

		sid = site.get_login_sid()
		return f"https://{self.domain or self.site}/desk?sid={sid}"


def get_app_trial_page_url():
	referer = frappe.request.headers.get("referer", "")
	if not referer:
		return None
	try:
		# parse the referer url
		site = urllib.parse.urlparse(referer).hostname
		# check if any product trial request exists for the site
		product_trial_name = frappe.db.get_value("Product Trial Request", {"site": site}, "product_trial")
		if product_trial_name:
			# Check site status
			# site_status = frappe.db.get_value("Site", site, "status")
			# if site_status in ("Active", "Inactive", "Suspended"):
			return f"/dashboard/signup?product={product_trial_name}"
	except Exception:
		frappe.log_error(title="App Trial Page URL Error")
		return None


def expire_long_pending_trial_requests():
	frappe.db.set_value(
		"Product Trial Request",
		{"status": "Pending", "creation": ("<", add_to_date(now_datetime(), hours=-6))},
		"status",
		"Expired",
		update_modified=False,
	)
