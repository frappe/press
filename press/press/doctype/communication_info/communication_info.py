# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_address, validate_phone_number
from frappe.utils.caching import redis_cache

COMMUNICATION_TYPE_LITERAL = Literal[
	"General", "Billing", "Incident", "Server Activity", "Site Activity", "Marketplace"
]


CHANNEL_TYPE_LITERAL = Literal["Email", "Phone Call"]


class CommunicationInfo(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		channel: DF.Literal["Email", "Phone Call"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Literal["General", "Billing", "Incident", "Server Activity", "Site Activity", "Marketplace"]
		value: DF.Data
	# end: auto-generated types

	# NOTE: For any changes in type, channel please update the same in helpers method

	def validate(self):
		if not self.parenttype or not self.parent:
			frappe.throw("parenttype and parent are required")

		if self.parenttype not in ("Team", "Site", "Server"):
			frappe.throw("parenttype must be one of 'Team', 'Site', 'Server'")

		if self.channel == "Phone Call" and self.type != "Incident":
			frappe.throw("Phone Call is available only for 'Incident'")

		if self.channel == "Email":
			validate_email_address(self.value, throw=True)

		if self.channel == "Phone Call":
			validate_phone_number(self.value, throw=True)

		# With every resource, all type of communication info is not allowed

		# For Team, all types are allowed

		if self.parenttype == "Server" and self.type not in ("General", "Server Activity", "Incident"):
			frappe.throw(f"Communication type '{self.type}' is not allowed for '{self.parenttype}'")

		if self.parenttype == "Site" and self.type not in ("General", "Site Activity"):
			frappe.throw(f"Communication type '{self.type}' is not allowed for 'Site'")


@redis_cache(ttl=10 * 60)
def get_communication_info(  # noqa: C901
	channel: CHANNEL_TYPE_LITERAL,
	communication_type: COMMUNICATION_TYPE_LITERAL,
	resource_type: Literal["Team", "Site", "Server", "Database Server"],
	resource_name: str,
) -> list[str]:
	# Do some changing in resource_type for specific cases
	if resource_type == "Database Server":
		resource_type = "Server"
		resource_name = frappe.db.get_value(
			"Server", {"database_server": resource_name, "status": ["!=", "Archived"]}, "name"
		)
		if not resource_name:
			return []

	# Try to look for resource specific communication info
	types = [communication_type]
	if communication_type != "General":
		types.append("General")
	infos = (
		frappe.get_all(
			"Communication Info",
			filters={
				"channel": channel,
				"type": ("in", types),
				"parenttype": resource_type,
				"parent": resource_name,
			},
			fields=["value", "type"],
		)
		or []
	)

	if communication_type != "General":
		# Check if we have any other type of communication info other than General
		other_type_infos = [d for d in infos if d.type != "General"]
		if other_type_infos:
			infos = other_type_infos
		# If nothing found, try to keep all including General communication info

	# If nothing found, pick team user email
	if not infos:
		if resource_type == "Team":
			if channel == "Email":
				infos.append({"type": "General", "value": frappe.get_value("Team", resource_name, "user")})
		elif resource_type in ("Site", "Server", "Database Server"):
			team = frappe.get_value(resource_type, resource_name, "team")
			if team:
				emails = get_communication_info(channel, communication_type, "Team", team)
				for email in emails:
					infos.append(
						{"type": "General", "value": email}
					)  # Marking as General, because doesn't matter at this point

	return list(set(d["value"] for d in infos if d.get("value")))


def update_communication_infos(  # noqa: C901
	resource_type: Literal["Team", "Site", "Server"],
	resource_name: str,
	values: list[dict[str, str]],
):
	"""
	values : [
			{
				"channel": "Email",
				"type": "General",
				"value": "email@example.com"
			}
		]
	"""

	if resource_type not in ("Team", "Site", "Server"):
		frappe.throw("resource_type must be one of 'Team', 'Site', 'Server'")

	# Remove values with empty value
	values = [value for value in values if value.get("value")]

	# Remove duplicates in values
	unique_values = []
	for value in values:
		if value not in unique_values:
			unique_values.append(value)
	values = unique_values

	# Fetch existing records
	records = frappe.get_all(
		"Communication Info",
		filters={
			"parenttype": resource_type,
			"parent": resource_name,
		},
		fields=["name", "channel", "type", "value"],
	)

	# Find which doesn't required anymore
	to_delete = []
	for record in records:
		found = False
		for value in values:
			if (
				record.channel == value.get("channel")
				and record.type == value.get("type")
				and record.value == value.get("value")
			):
				found = True
				break
		if not found:
			to_delete.append(record.name)

	# Find which to add
	to_add = []
	for value in values:
		found = False
		for record in records:
			if (
				record.channel == value.get("channel")
				and record.type == value.get("type")
				and record.value == value.get("value")
			):
				found = True
				break
		if not found:
			to_add.append(value)

	# Validate no multiple `Billing` type of communication info
	if resource_type == "Team":
		billing_count = sum(1 for value in values if value.get("type") == "Billing")
		if billing_count > 1:
			frappe.throw("For Billing, only one email can be configured")

	# Delete unwanted
	if to_delete:
		frappe.db.delete("Communication Info", {"name": ("in", to_delete)})

	# Add new
	for value in to_add:
		doc = frappe.get_doc(
			{
				"doctype": "Communication Info",
				"parenttype": resource_type,
				"parent": resource_name,
				"channel": value.get("channel"),
				"type": value.get("type"),
				"value": value.get("value"),
				"parentfield": "communication_infos",
			}
		)
		doc.insert(ignore_permissions=True)


def delete_communication_info(
	resource_type: Literal["Team", "Site", "Server"],
	resource_name: str,
	channel: CHANNEL_TYPE_LITERAL | None = None,
	communication_type: COMMUNICATION_TYPE_LITERAL | None = None,
):
	payload = {
		"parenttype": resource_type,
		"parent": resource_name,
	}
	if channel:
		payload["channel"] = channel
	if communication_type:
		payload["type"] = communication_type
	frappe.db.delete("Communication Info", payload)
