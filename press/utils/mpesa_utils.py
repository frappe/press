# Copyright (c) 2019, Frappe Technologies and contributors
# License: MIT. See LICENSE

import datetime
import json

import frappe


def create_mpesa_request_log(
	data,
	integration_type=None,
	service_name=None,
	name=None,
	error=None,
	status="Queued",
	request_headers=None,
	output=None,
	**kwargs,
):
	"""
	DEPRECATED: The parameter integration_type will be removed in the next major release.
	Use is_remote_request instead.
	"""
	if integration_type == "Remote":
		kwargs["is_remote_request"] = 1

	elif integration_type == "Subscription Notification":
		kwargs["request_description"] = integration_type

	if isinstance(data, str):
		data = json.loads(data)

	request_log = frappe.get_doc(
		{
			"doctype": "Mpesa Request Log",
			"integration_request_service": service_name,
			"request_headers": get_json(request_headers),
			"data": get_json(data),
			"output": get_json(output),
			"error": get_json(error),
			"request_id": name,
			"status": status,
		}
	)
	request_log.insert(ignore_permissions=True)

	return request_log


def get_json(obj):
	return obj if isinstance(obj, str) else frappe.as_json(obj, indent=1)


def json_handler(obj):
	if isinstance(obj, datetime.date | datetime.timedelta | datetime.datetime):
		return str(obj)
	return None
