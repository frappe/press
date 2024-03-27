import re
import typing

import dockerfile
import frappe
from frappe.core.utils import find
from frappe.utils import now_datetime, rounded
from press.utils import log_error

# Reference:
# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
ansi_escape_rx = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

if typing.TYPE_CHECKING:
	from re import Match
	from typing import Any, Generator, TypedDict
	from frappe.types import DF

	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_build_step.deploy_candidate_build_step import (
		DeployCandidateBuildStep,
	)

	BuildOutput = list[str] | Generator[str, Any, None]
	PushOutput = list[dict] | Generator[dict, Any, None]
	IndexSplit = TypedDict(
		"IndexSplit",
		{
			"index": int,
			"line": str,
			"is_unusual": bool,
		},
	)


class DockerBuildOutputParser:
	"""
	Parses `docker build` raw output and updates Deploy Candidate.

	Output can be generated from a remote builder (agent) or from a build running
	on press itself.

	In case of a remote build, due to the way agent updates are propagated, all
	lines are updated when agent is polled, and so output is looped N! times.
	"""

	def __init__(self, dc: "DeployCandidate") -> None:
		self.dc = dc
		self.is_remote = dc.is_docker_remote_builder_used
		self.last_updated = now_datetime()

		# Used to generate output and track parser state
		self.lines: list[str] = []
		self.steps: dict[int, "DeployCandidateBuildStep"] = frappe._dict()

		# Convenience map used to update build steps
		self.steps_by_step_slug = {bs.step_slug: bs for bs in dc.build_steps}

	# `output` can be from local or remote build
	def parse_and_update(self, output: "BuildOutput"):
		for raw_line in output:
			self._parse_line_handle_exc(raw_line)
		self._end_parsing()

	def _parse_line_handle_exc(self, raw_line: str):
		try:
			self._parse_line(raw_line)
			self._update_dc_build_output()
		except Exception:
			self._log_error(raw_line)

	def _log_error(self, raw_line: str):
		try:
			log_error(
				title="Build Output Parse Error",
				message=f"Error in parsing line: `{raw_line}`",
				doc=self.dc,
			)
		except Exception:
			pass

	def _update_dc_build_output(self):
		if self.is_remote:
			return

		sec_since_last_update = (now_datetime() - self.last_updated).total_seconds()
		if sec_since_last_update <= 1:
			return

		self.build_output = "".join(self.lines)
		self.save(ignore_version=True)
		frappe.db.commit()

		self.last_update = now_datetime()

	def _parse_line(self, raw_line: str):
		escaped_line = ansi_escape(raw_line)

		# append before stripping to preserve '\n'
		self.lines.append(escaped_line)
		if not escaped_line:
			return

		stripped_line = escaped_line.strip()

		# Separate step index from line
		split = self._get_step_index_split(stripped_line)
		line = split["line"]

		# Final stage of the build
		if line.startswith("writing image"):
			self._set_docker_image_id(line)

		# Updates build step properties
		elif split["index"] in self.steps:
			self._update_dc_build_step(split)

		# Sets build step to running and adds it to self.steps
		else:
			self._add_step_to_steps_dict(split)

	def _end_parsing(self):
		if self.is_remote:
			self.dc.last_updated = now_datetime()

		self.dc.build_output = "".join(self.lines)
		self.dc.save()
		frappe.db.commit()

	def _set_docker_image_id(self, line: str):
		self.dc.docker_image_id = line.split()[2].split(":")[1]

	def _update_dc_build_step(self, split: "IndexSplit"):
		step = self.steps.get(split["index"])
		if not step:
			return

		line = split["line"]
		if split["is_unusual"]:
			step.output += line + "\n"
		elif line.startswith("sha256:"):
			step.hash = line[7:]
		elif line.startswith("DONE"):
			step.status = "Success"
			step.duration = float(line.split()[1][:-1])
		elif line == "CACHED":
			step.status = "Success"
			step.cached = True
		elif line.startswith("ERROR"):
			step.status = "Failure"
			step.output += line[7:] + "\n"
		else:
			_, _, output = line.partition(" ")
			step.output += output + "\n"

	def _add_step_to_steps_dict(self, split: "IndexSplit"):
		line = split["line"]
		if not line.startswith("[stage-"):
			return

		name = line.split("]", maxsplit=1)[1].strip()
		if not name.startswith("RUN"):
			return

		if not (match := re.search("`#stage-(.*)`", name)):
			return

		name, _, step_slug = get_name_and_slugs(name, match)
		step = self.steps_by_step_slug.get(step_slug)
		if not step:
			return

		index = split["index"]
		step.step_index = index
		step.command = name
		step.status = "Running"
		step.output = ""

		self.steps[index] = step

	def _get_step_index_split(self, line: str) -> "IndexSplit":
		splits = line.split(maxsplit=1)
		if len(splits) != 2:
			index = (sorted(self.steps)[-1],)
			return dict(index=index, line=line, is_unusual=True)

		index_str, line = splits
		try:
			index = int(index_str[1:])
			return dict(index=index, line=line, is_unusual=False)
		except ValueError:
			index = (sorted(self.steps)[-1],)
			return dict(index=index, line=line, is_unusual=True)


def ansi_escape(text: str) -> str:
	return ansi_escape_rx.sub("", text)


def get_name_and_slugs(name: str, match: "Match[str]") -> tuple[str, str, str]:
	# Returns: name, stage_slug, step_slug
	if flags := dockerfile.parse_string(name)[0].flags:
		name = name.replace(flags[0], "")

	old = match.group(0)
	name = name.replace(old, "")
	name = name.strip()
	name = name.replace("   ", " \\\n  ")[4:]

	stage_slug, step_slug = match.group(1).split("-", maxsplit=1)
	return name, stage_slug, step_slug


class UploadStepUpdater:
	upload_step: "DeployCandidateBuildStep"

	def __init__(self, dc: "DeployCandidate") -> None:
		self.dc = dc
		self.is_remote = dc.is_docker_remote_builder_used
		self.output: list[dict] = []

		# Used only if not remote
		self.start_time = now_datetime()
		self.last_updated = now_datetime()

	def start(self):
		self.upload_step = self.dc.get_first_step("stage_slug", "upload")
		if self.upload_step.status == "Running":
			pass

		self.upload_step.status = "Running"
		self._update_upload_step_output()

	def process(self, output: "PushOutput"):
		for line in output:
			self._process_single_line(line)

		# If remote, duration is accumulated
		if self.is_remote:
			duration = (now_datetime() - self.dc.last_updated).total_seconds()
			self.upload_step.duration += rounded(duration, 1)

		# If not remote, duration is calculated once
		else:
			duration = (now_datetime() - self.start_time).total_seconds()
			self.upload_step.duration = rounded(duration, 1)

			# If remote, this has to be set on Agent Job success
			self.upload_step.status = "Success"
		self._update_upload_step_output()

	def end(self, status: 'DF.Literal["Success", "Failure"]'):
		# Used only if the build is running locally
		self.upload_step.status = status
		self._update_upload_step_output()

	def _process_single_line(self, line: dict):
		self._update_output(line)
		if self.is_remote:
			return

		# If not remote, upload step output is updated every 1 second
		now = now_datetime()
		if (now - self.last_updated).total_seconds() <= 1:
			return

		self._update_upload_step_output()
		self.last_updated = now

	def _update_output(self, line: dict):
		line_id = line.get("id")
		if not line_id:
			return

		line_status = line.get("status", "")
		line_progress = line.get("progress", "")
		line_str = f"{line_id}: {line_status} {line_progress}"

		if existing := find(
			self.output,
			lambda x: x["id"] == line_id,
		):
			existing["output"] = line_str
		else:
			self.output.append({"id": line_id, "output": line_str})

	def _update_upload_step_output(self):
		output_lines = [line["output"] for line in self.output]
		self.upload_step.output = "\n".join(output_lines)
		self.dc.save(ignore_version=True)
		frappe.db.commit()
