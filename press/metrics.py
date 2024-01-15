# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from prometheus_client import (
	CollectorRegistry,
	Gauge,
	generate_latest,
)
from werkzeug.wrappers import Response
import frappe
from frappe.utils import cint


class MetricsRenderer:
	def __init__(self, path, status_code=None):
		self.path = path
		self.registry = CollectorRegistry(auto_describe=True)

	def metrics(self):
		suspended_builds = Gauge(
			"press_builds_suspended", "Are docker builds suspended", registry=self.registry
		)
		suspended_builds.set(
			cint(frappe.db.get_value("Press Settings", None, "suspend_builds"))
		)
		return generate_latest(self.registry).decode("utf-8")

	def can_render(self):
		if self.path in ("metrics",):
			return True

	def render(self):
		response = Response()
		response.mimetype = "text"
		response.data = self.metrics()
		return response
