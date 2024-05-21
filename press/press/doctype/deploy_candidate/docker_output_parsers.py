import re
import typing

import dockerfile
import frappe
from frappe.core.utils import find
from frappe.utils import now_datetime, rounded

# Reference:
# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
ansi_escape_rx = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
done_check_rx = re.compile(r"#\d+\sDONE\s\d+\.\d+")

if typing.TYPE_CHECKING:
	from typing import Any, Generator, Optional, TypedDict

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

	_steps_by_step_slug: "Optional[dict[tuple[str, str], DeployCandidateBuildStep]]"

	def __init__(self, dc: "DeployCandidate") -> None:
		self.dc = dc
		self.is_remote = dc.is_docker_remote_builder_used
		self.last_updated = now_datetime()

		# Used to generate output and track parser state
		self.lines: list[str] = []
		self.error_lines: list[str] = []
		self.steps: dict[int, "DeployCandidateBuildStep"] = frappe._dict()
		self._steps_by_step_slug = None

	# Convenience map used to update build steps
	@property
	def steps_by_step_slug(self):
		if not self._steps_by_step_slug:
			self._steps_by_step_slug = {
				(bs.stage_slug, bs.step_slug): bs for bs in self.dc.build_steps
			}
		return self._steps_by_step_slug

	# `output` can be from local or remote build
	def parse_and_update(self, output: "BuildOutput"):
		for raw_line in output:
			self._parse_line_handle_exc(raw_line)
		self._end_parsing()

	def _parse_line_handle_exc(self, raw_line: str):
		self._parse_line(raw_line)
		self._update_dc_build_output()

	def _update_dc_build_output(self):
		# Output saved at the end of parsing all lines
		if self.is_remote:
			return

		sec_since_last_update = (now_datetime() - self.last_updated).total_seconds()
		if sec_since_last_update <= 1:
			return

		self.flush_output()
		self.last_update = now_datetime()

	def flush_output(self, commit: bool = True):
		self.dc.build_output = "".join(self.lines)
		self.dc.build_error = "".join(self.error_lines)

		self.dc.save(ignore_version=True, ignore_permissions=True)
		if commit:
			frappe.db.commit()

	def _parse_line(self, raw_line: str):
		escaped_line = ansi_escape(raw_line)

		# append before stripping to preserve '\n'
		self.lines.append(escaped_line)

		# check if line is part of build error and append
		self._append_error_line(escaped_line)

		stripped_line = escaped_line.strip()
		if not stripped_line:
			return

		# Separate step index from line
		if not (split := self._get_step_index_split(stripped_line)):
			return

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

	def _append_error_line(self, escaped_line: str):
		no_errors = len(self.error_lines) == 0

		# Recorded errors not build failing errors
		if not no_errors and re.match(done_check_rx, escaped_line):
			self.error_lines = []
			return

		if no_errors and "ERROR:" not in escaped_line:
			return

		splits = escaped_line.split(" ", maxsplit=1)

		# If no_errors then first "ERROR:" is the start of error log.
		if no_errors and len(splits) > 1 and splits[1].startswith("ERROR:"):
			self.error_lines.append(splits[1])

		# Build error ends the build, once an error is encountered
		# remaining build output lines belong to the error log.
		else:
			self.error_lines.append(escaped_line)

	def _end_parsing(self):
		if self.is_remote:
			self.dc.last_updated = now_datetime()

		self.flush_output(True)

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

		stage_slug, step_slug = match.group(1).split("-", maxsplit=1)
		step = self.steps_by_step_slug.get((stage_slug, step_slug))
		if not step:
			return

		index = split["index"]
		step.step_index = index
		step.command = get_command(name)
		step.status = "Running"
		step.output = ""

		self.steps[index] = step

	def _get_step_index_split(self, line: str) -> "Optional[IndexSplit]":
		splits = line.split(maxsplit=1)
		keys = sorted(self.steps)
		if len(splits) != 2 and len(keys) == 0:
			return None

		try:
			index_str, line = splits
			is_unusual = False
			index = int(index_str[1:])
		except ValueError:
			is_unusual = True
			index = keys[-1] if len(keys) else -1

		if index == -1:
			return None

		return dict(index=index, line=line, is_unusual=is_unusual)


def ansi_escape(text: str) -> str:
	return ansi_escape_rx.sub("", text)


def get_command(name: str) -> str:
	# Strip docker flags and commands from the line
	line = dockerfile.parse_string(name)[0]
	command = " ".join(line.value).strip()
	if not command:
		command: str = line.original.split(maxsplit=1)[1]
	command = command.split("`#stage-", maxsplit=1)[0]

	# Remove line fold slashes
	splits = [p.strip() for p in command.split(" \\\n")]

	# Strip multiple internal whitespaces
	for i in range(len(splits)):
		s = splits[i]
		splits[i] = " ".join([p.strip() for p in s.split() if len(p)])

	return "\n".join([p for p in splits if len(p)])


class UploadStepUpdater:
	"""
	Processes the output of `client.images.push` and uses it to update
	the last `build_step` which pertains to uploading the image to the
	registry.

	Similar to DockerBuildOutputParser, this can process the output from
	a remote (agent) or local (press) builder docker push.
	"""

	_upload_step: "DeployCandidateBuildStep | None"

	def __init__(self, dc: "DeployCandidate") -> None:
		self.dc = dc
		self.is_remote = dc.is_docker_remote_builder_used
		self.output: list[dict] = []

		# Used only if not remote
		self.start_time = now_datetime()
		self.last_updated = now_datetime()
		self._upload_step = None

	@property
	def upload_step(self) -> "DeployCandidateBuildStep | None":
		if not self._upload_step:
			self._upload_step = self.dc.get_step("upload", "image")
		return self._upload_step

	def start(self):
		if not self.upload_step:
			return

		if self.upload_step.status == "Running":
			return

		self.upload_step.status = "Running"
		self.flush_output()

	def process(self, output: "PushOutput"):
		if not self.upload_step:
			return

		for line in output:
			self._process_single_line(line)

		# If remote, duration is accumulated
		last_update = self.start_time

		# If not remote, duration is calculated once
		if self.is_remote:
			last_update = self.dc.last_updated

		duration = (now_datetime() - last_update).total_seconds()
		self.upload_step.duration = rounded(duration, 1)
		self.flush_output()

	def end(self, status: 'Optional[DF.Literal["Success", "Failure"]]'):
		if not self.upload_step:
			return

		# Used only if the build is running locally
		self.upload_step.status = status
		self.flush_output()

	def _process_single_line(self, line: dict):
		self._update_output(line)
		if self.is_remote:
			return

		# If not remote, upload step output is updated every 1 second
		now = now_datetime()
		if (now - self.last_updated).total_seconds() <= 1:
			return

		self.flush_output()
		self.last_updated = now

	def _update_output(self, line: dict):
		if error := line.get("error"):
			message = line.get("errorDetail", {}).get("message", error)
			line_str = f"no_id: Error {message}"
			self.output.append({"id": "no_id", "output": line_str, "status": "Error"})
			return

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
			self.output.append({"id": line_id, "output": line_str, "status": line_status})

	def flush_output(self, commit: bool = True):
		if not self.upload_step:
			return

		output_lines = []
		for line in self.output:
			output_lines.append(line["output"])
			status = line.get("status")

			if status == "Error":
				self.upload_step.status = "Failure"
			elif status == "Pushed":
				self.upload_step.status = "Success"

		self.upload_step.output = "\n".join(output_lines)
		self.dc.save(ignore_version=True, ignore_permissions=True)
		if commit:
			frappe.db.commit()
