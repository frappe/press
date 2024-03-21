# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AgentJobType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.agent_job_type_step.agent_job_type_step import (
			AgentJobTypeStep,
		)

		disabled_auto_retry: DF.Check
		max_retry_count: DF.Int
		request_method: DF.Literal["POST", "DELETE"]
		request_path: DF.Data | None
		steps: DF.Table[AgentJobTypeStep]
	# end: auto-generated types

	pass
