from unittest import TestCase

from press.press.doctype.deploy_candidate.docker_output_parsers import get_command


class TestDockerOutputParsers(TestCase):
	def test_get_command_strips_run_flags_and_stage_marker(self):
		name = "RUN --mount=type=cache,target=/root/.cache pip install -e apps/frappe `#stage-install-frappe`"

		self.assertEqual(get_command(name), "pip install -e apps/frappe")

	def test_get_command_normalizes_line_folds(self):
		name = "RUN apt-get update \\\n && apt-get install -y curl \\\n && rm -rf /var/lib/apt/lists/* `#stage-setup-apt`"

		self.assertEqual(
			get_command(name),
			"apt-get update\n&& apt-get install -y curl\n&& rm -rf /var/lib/apt/lists/*",
		)

	def test_get_command_keeps_json_form_run(self):
		name = 'RUN ["python", "-m", "compileall", "apps"] `#stage-compile-assets`'

		self.assertEqual(get_command(name), '["python", "-m", "compileall", "apps"]')

	def test_get_command_preserves_quoted_arguments(self):
		name = 'RUN echo "hello world" `#stage-print-message`'

		self.assertEqual(get_command(name), 'echo "hello world"')
