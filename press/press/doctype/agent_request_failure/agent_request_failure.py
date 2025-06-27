# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document

from press.agent import Agent
from press.utils import log_error


class AgentRequestFailure(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		error: DF.Code
		failure_count: DF.Int
		server: DF.DynamicLink
		server_type: DF.Link
		traceback: DF.Code
	# end: auto-generated types

	pass

	def before_insert(self):
		# TODO: Remove once tests pass
		if frappe.flags.in_test:
			print(frappe.get_traceback(with_context=True))


def is_server_archived(failure):
	# Server was archived more than an hour ago
	server = frappe.db.get_value(failure.server_type, failure.server, ["status", "modified"], as_dict=True)
	if (server.status == "Archived") and (server.modified < frappe.utils.add_to_date(None, hours=-1)):
		return True
	return False


def remove_old_failures():
	failures = frappe.get_all(
		"Agent Request Failure",
		["name", "server_type", "server", "failure_count"],
		order_by="creation ASC",
	)
	for failure in failures:
		delta = 0
		try:
			agent = Agent(failure.server, failure.server_type)
			agent.raw_request("GET", "ping", raises=True, timeout=(1, 5))
		except (requests.ConnectTimeout, requests.ReadTimeout, requests.ConnectionError):
			# Server is still down, either because
			# 1. Couldn't connect
			# 2. Couldn't respond in time,
			# increment the failure count
			delta = 1
		except requests.RequestException:
			# Something still wrong with the connection, ignore for now.
			pass
		except Exception:
			# Something weird happened, probably not related to requests
			log_error("Agent Status Check Failure", failure=failure)
		else:
			# Server responded, aggressively decrement the failure count
			# Aggressively
			delta = -100

		if delta:
			if failure.failure_count + delta <= 0 or is_server_archived(failure):
				frappe.delete_doc("Agent Request Failure", failure.name)
			else:
				frappe.db.set_value(
					"Agent Request Failure",
					failure.name,
					"failure_count",
					failure.failure_count + delta,
				)
