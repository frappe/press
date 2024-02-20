# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.utils import ttl_cache


class AgentJobType(Document):
	def on_update(self):
		get_retryable_job_types_and_max_retry_count.cache.invalidate()


@ttl_cache()
def get_retryable_job_types_and_max_retry_count():
	job_types, max_retry_per_job_type = [], {}
	for job_type in frappe.get_all(
		"Agent Job Type",
		filters={"disabled_auto_retry": 0, "max_retry_count": [">", 0]},
		fields=["name", "max_retry_count"],
	):
		job_types.append(job_type["name"])
		max_retry_per_job_type[job_type["name"]] = job_type["max_retry_count"]

	return job_types, max_retry_per_job_type
