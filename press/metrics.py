# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from prometheus_client import (
	CollectorRegistry,
	generate_latest,
)
from werkzeug.wrappers import Response


class MetricsRenderer:
	def __init__(self, path):
		self.path = path

	def metrics(self):
		registry = CollectorRegistry(auto_describe=True)
		return generate_latest(registry).decode("utf-8")

	def can_render(self):
		if self.path in ("metrics",):
			return True

	def render(self):
		response = Response()
		response.mimetype = "text"
		response.data = self.metrics()
		return response
