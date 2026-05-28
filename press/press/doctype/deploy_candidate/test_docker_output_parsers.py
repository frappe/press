# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for deploy_candidate/docker_output_parsers.py.

Where possible, methods are tested in isolation using lightweight MagicMock
objects so that no Frappe database round-trips are required.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.deploy_candidate.docker_output_parsers import (
	CloneOutputParser,
	DockerBuildOutputParser,
	UploadStepUpdater,
	ansi_escape,
)

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _make_dc_mock(build_steps=None):
	"""Return a minimal DeployCandidateBuild-like MagicMock."""
	dc = MagicMock()
	dc.build_steps = build_steps or []
	dc.build_output = ""
	dc.build_error = ""
	dc.last_updated = datetime.now()
	return dc


# ══════════════════════════════════════════════════════════════════════════════
# ansi_escape
# ══════════════════════════════════════════════════════════════════════════════


class TestAnsiEscape(FrappeTestCase):
	"""ansi_escape() strips ANSI escape codes from a string."""

	def test_plain_string_unchanged(self):
		self.assertEqual(ansi_escape("hello world"), "hello world")

	def test_strips_color_code(self):
		colored = "\x1b[32mGreen text\x1b[0m"
		self.assertEqual(ansi_escape(colored), "Green text")

	def test_strips_bold_code(self):
		bold = "\x1b[1mBold\x1b[0m"
		self.assertEqual(ansi_escape(bold), "Bold")

	def test_strips_cursor_movement(self):
		with_cursor = "\x1b[1A\x1b[2K"
		self.assertEqual(ansi_escape(with_cursor), "")

	def test_empty_string(self):
		self.assertEqual(ansi_escape(""), "")

	def test_multiple_escape_sequences(self):
		text = "\x1b[31mERROR\x1b[0m: \x1b[33mwarning\x1b[0m"
		result = ansi_escape(text)
		self.assertNotIn("\x1b", result)
		self.assertIn("ERROR", result)
		self.assertIn("warning", result)


# ══════════════════════════════════════════════════════════════════════════════
# DockerBuildOutputParser — _append_error_line
# ══════════════════════════════════════════════════════════════════════════════


class TestDockerBuildOutputParserAppendErrorLine(FrappeTestCase):
	"""_append_error_line() accumulates error lines and clears them on DONE."""

	def _make_parser(self):
		return DockerBuildOutputParser(_make_dc_mock())

	def test_non_error_line_not_added_when_no_errors(self):
		p = self._make_parser()
		p._append_error_line("#1 [stage-install] RUN pip install\n")
		self.assertEqual(p.error_lines, [])

	def test_first_error_line_starts_error_log(self):
		p = self._make_parser()
		p._append_error_line("#1 ERROR: pip install failed\n")
		self.assertEqual(len(p.error_lines), 1)
		self.assertIn("ERROR:", p.error_lines[0])

	def test_subsequent_lines_appended_to_error_log(self):
		p = self._make_parser()
		p._append_error_line("#1 ERROR: first\n")
		p._append_error_line("Traceback (most recent call last):\n")
		self.assertEqual(len(p.error_lines), 2)

	def test_done_line_clears_error_log(self):
		p = self._make_parser()
		p._append_error_line("#1 ERROR: first\n")
		# A "#N DONE X.Xs" line clears the error log
		p._append_error_line("#1 DONE 0.5\n")
		self.assertEqual(p.error_lines, [])


# ══════════════════════════════════════════════════════════════════════════════
# DockerBuildOutputParser — _parse_line (lines accumulation)
# ══════════════════════════════════════════════════════════════════════════════


class TestDockerBuildOutputParserParseLine(FrappeTestCase):
	def _make_parser(self):
		return DockerBuildOutputParser(_make_dc_mock())

	def test_plain_line_appended_to_lines(self):
		p = self._make_parser()
		p._parse_line("some build output\n")
		self.assertEqual(len(p.lines), 1)
		self.assertIn("some build output", p.lines[0])

	def test_ansi_codes_stripped_from_accumulated_lines(self):
		p = self._make_parser()
		p._parse_line("\x1b[32mSuccess\x1b[0m\n")
		self.assertNotIn("\x1b", p.lines[0])
		self.assertIn("Success", p.lines[0])

	def test_empty_line_appended_but_not_processed_further(self):
		p = self._make_parser()
		p._parse_line("\n")
		self.assertEqual(len(p.lines), 1)
		# No steps added for blank lines
		self.assertEqual(len(p.steps), 0)

	def test_image_id_set_from_writing_image_line(self):
		p = self._make_parser()
		dc = p.dc
		# Simulate a step index already in self.steps to reach the image-id branch
		# The writing-image line format: "#N writing image sha256:<id>"
		# We need split[0] = "#N", split[1] = "writing image sha256:<id>"
		p.steps[1] = MagicMock()
		p._parse_line("#1 writing image sha256:abcdef1234\n")
		self.assertEqual(dc.docker_image_id, "abcdef1234")


# ══════════════════════════════════════════════════════════════════════════════
# DockerBuildOutputParser — _update_dc_build_step
# ══════════════════════════════════════════════════════════════════════════════


class TestDockerBuildOutputParserUpdateStep(FrappeTestCase):
	def _make_parser_with_step(self, index=1):
		p = DockerBuildOutputParser(_make_dc_mock())
		step = MagicMock()
		step.output = ""
		step.status = "Running"
		p.steps[index] = step
		return p, step

	def test_done_line_sets_status_success_and_duration(self):
		p, step = self._make_parser_with_step()
		split = {"index": 1, "line": "DONE 1.5s", "is_unusual": False}
		p._update_dc_build_step(split)
		self.assertEqual(step.status, "Success")
		self.assertAlmostEqual(step.duration, 1.5)

	def test_cached_line_sets_status_success_and_cached_flag(self):
		p, step = self._make_parser_with_step()
		split = {"index": 1, "line": "CACHED", "is_unusual": False}
		p._update_dc_build_step(split)
		self.assertEqual(step.status, "Success")
		self.assertTrue(step.cached)

	def test_error_line_sets_status_failure(self):
		p, step = self._make_parser_with_step()
		split = {"index": 1, "line": "ERROR pip install failed", "is_unusual": False}
		p._update_dc_build_step(split)
		self.assertEqual(step.status, "Failure")

	def test_sha256_line_sets_hash(self):
		p, step = self._make_parser_with_step()
		split = {"index": 1, "line": "sha256:deadbeef", "is_unusual": False}
		p._update_dc_build_step(split)
		self.assertEqual(step.hash, "deadbeef")

	def test_unusual_line_appended_to_output(self):
		p, step = self._make_parser_with_step()
		split = {"index": 1, "line": "some unusual output", "is_unusual": True}
		p._update_dc_build_step(split)
		self.assertIn("some unusual output", step.output)

	def test_missing_step_is_noop(self):
		p = DockerBuildOutputParser(_make_dc_mock())
		split = {"index": 99, "line": "DONE 1.0s", "is_unusual": False}
		p._update_dc_build_step(split)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# CloneOutputParser — _parse_app_output_map
# ══════════════════════════════════════════════════════════════════════════════


class TestCloneOutputParserParseAppOutputMap(FrappeTestCase):
	"""_parse_app_output_map() is a pure method — no DB required."""

	def _make_parser(self):
		dcb = MagicMock()
		return CloneOutputParser(dcb)

	def test_parses_git_clone_entry(self):
		parser = self._make_parser()
		output = ["git clone frappe\nCloning into 'frappe'...\n"]
		result = parser._parse_app_output_map(output)
		self.assertIn("frappe", result)

	def test_parses_cached_clone_entry(self):
		parser = self._make_parser()
		output = ["git clone frappe CACHED\nUsing cached clone.\n"]
		result = parser._parse_app_output_map(output)
		self.assertIn("frappe", result)

	def test_parses_failed_clone_entry(self):
		parser = self._make_parser()
		output = ["Failed to clone repository for frappe - authentication failed\n"]
		result = parser._parse_app_output_map(output)
		self.assertIn("frappe", result)

	def test_empty_output_returns_empty_map(self):
		parser = self._make_parser()
		self.assertEqual(parser._parse_app_output_map([]), {})

	def test_multiple_apps(self):
		parser = self._make_parser()
		output = [
			"git clone frappe\nCloned.\n",
			"git clone erpnext\nCloned.\n",
		]
		result = parser._parse_app_output_map(output)
		self.assertIn("frappe", result)
		self.assertIn("erpnext", result)


# ══════════════════════════════════════════════════════════════════════════════
# UploadStepUpdater — _update_output
# ══════════════════════════════════════════════════════════════════════════════


class TestUploadStepUpdaterUpdateOutput(FrappeTestCase):
	"""_update_output() is a pure dict-processing method — no DB required."""

	def _make_updater(self):
		return UploadStepUpdater(_make_dc_mock())

	def test_error_line_added_with_error_status(self):
		u = self._make_updater()
		line = {"error": "push failed", "errorDetail": {"message": "auth error"}}
		u._update_output(line)
		self.assertEqual(len(u.output), 1)
		self.assertEqual(u.output[0]["status"], "Error")

	def test_normal_push_line_added(self):
		u = self._make_updater()
		line = {"id": "layer1", "status": "Pushing", "progress": "50%"}
		u._update_output(line)
		self.assertEqual(len(u.output), 1)
		self.assertIn("layer1", u.output[0]["output"])

	def test_same_id_updates_existing_entry(self):
		u = self._make_updater()
		u._update_output({"id": "layer1", "status": "Pushing", "progress": "10%"})
		u._update_output({"id": "layer1", "status": "Pushed", "progress": ""})
		self.assertEqual(len(u.output), 1)
		self.assertIn("Pushed", u.output[0]["output"])

	def test_line_without_id_is_skipped(self):
		u = self._make_updater()
		u._update_output({"status": "Digest"})
		self.assertEqual(len(u.output), 0)

	def test_multiple_different_layers(self):
		u = self._make_updater()
		u._update_output({"id": "layer1", "status": "Pushing", "progress": ""})
		u._update_output({"id": "layer2", "status": "Pushing", "progress": ""})
		self.assertEqual(len(u.output), 2)
