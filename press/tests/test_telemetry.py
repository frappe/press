from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.utils.telemetry import _pulse_post, pulse_identify


@patch(
	"press.utils.telemetry._pulse_credentials",
	return_value=("pulse.example.com", "test-key"),
)
class TestPulsePost(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_pulse_identify_enqueues_without_kwarg_collision_with_frappe_enqueue(self, _credentials):
		# Regression: _pulse_post forwarded its Pulse API method as a `method` kwarg,
		# which collided with frappe.enqueue's own first parameter `method` and raised
		# "TypeError: enqueue() got multiple values for argument 'method'" during signup.
		pulse_identify("test-team", {"plan": "trial"})

	def test_pulse_post_synchronous_path_posts_to_pulse_api_method(self, _credentials):
		with patch("press.utils.telemetry.requests.post") as post:
			_pulse_post("identify", {"team": "test-team"})
		post.assert_called_once()
		self.assertEqual(
			post.call_args.args[0],
			"https://pulse.example.com/api/method/pulse.api.identify",
		)
