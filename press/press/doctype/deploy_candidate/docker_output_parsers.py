from __future__ import annotations

import json
import re
import typing
from typing import Literal

import dockerfile
import frappe
from frappe.core.utils import find
from frappe.utils import now_datetime, rounded

# Reference:
# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
ansi_escape_rx = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
done_check_rx = re.compile(r"#\d+\sDONE\s\d+\.\d+")

if typing.TYPE_CHECKING:
	from collections.abc import Generator
	from typing import Any

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.deploy_candidate_build_step.deploy_candidate_build_step import (
		DeployCandidateBuildStep,
	)

	BuildOutput = list[str] | Generator[str, Any, None]
	PushOutput = list[dict] | Generator[dict, Any, None]


class IndexSplit(typing.TypedDict):
	index: int
	line: str
	is_unusual: bool


class DockerBuildOutputParser:
	"""
	Parses `docker build` raw output and updates Deploy Candidate.

	Due to the way agent updates are propagated, all lines are updated
	when agent is polled, and so output is looped N! times.
	"""

	_steps_by_step_slug: dict[tuple[str, str], DeployCandidateBuildStep] | None

	def __init__(self, dc: "DeployCandidateBuild") -> None:
		self.dc = dc
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
			self._steps_by_step_slug = {(bs.stage_slug, bs.step_slug): bs for bs in self.dc.build_steps}
		return self._steps_by_step_slug

	def parse_and_update(self, output: "BuildOutput"):
		for raw_line in output:
			self._parse_line_handle_exc(raw_line)
		self._end_parsing()

	def _parse_line_handle_exc(self, raw_line: str):
		self._parse_line(raw_line)

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
		elif line == "CACHED" or "found in store. Extracting and setting up" in line:
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

	def _get_step_index_split(self, line: str) -> "IndexSplit | None":
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
	command = " ".join(line.value).strip() or line.original.split(maxsplit=1)[1]
	command = command.split("`#stage-", maxsplit=1)[0]

	# Remove line fold slashes
	splits = [p.strip() for p in command.split(" \\\n")]

	# Strip multiple internal whitespaces
	for i in range(len(splits)):
		s = splits[i]
		splits[i] = " ".join([p.strip() for p in s.split() if len(p)])

	return "\n".join([p for p in splits if len(p)])


class CloneOutputParser:
	"""
	Parses `git clone` output and updates Deploy Candidate Clone Steps.

	Two categories of failures:
	1. Early failures - job failed before producing any clone output (traceback only)
	2. Output-based failures - job produced output but a specific app clone failed
	"""

	def __init__(self, dcb: "DeployCandidateBuild") -> None:
		self.dcb = dcb

	def _parse_app_output_map(self, clone_output: list) -> dict[str, str]:
		"""
		Parse a list of output entries into a map of {app_name: output}.
		Each entry is either:
		- "git clone <app>\n..." (normal or cached)
		- "Failed to clone repository for <app> - ..." (output-based failure)
		"""
		output_map = {}
		for entry in clone_output:
			first_line = entry.splitlines()[0] if entry else ""
			if first_line.startswith("git clone "):
				app_name = first_line.replace("git clone ", "").replace(" CACHED", "").strip()
				output_map[app_name] = entry
			elif first_line.startswith("Failed to clone repository for "):
				app_name = first_line.replace("Failed to clone repository for ", "").split(" - ")[0].strip()
				output_map[app_name] = entry
		return output_map

	def _parse_failed_output(self, job: AgentJob) -> dict[str, str] | None:
		"""
		Handle early failures where the job failed before producing clone output.
		Extracts app name from the job traceback.
		"""
		if job.status != "Failure" or not job.traceback:
			return None
		return self._parse_app_output_map([job.traceback])

	def _get_clone_step(self, job: AgentJob) -> str | None:
		"""Gets the name of the clone step for the given job, if it exists."""
		step = frappe.db.get_value(
			"Agent Job Step",
			filters={"agent_job": job.name, "step_name": "Clone Repositories"},
		)
		if not step:
			return None

		return step

	def _get_output_from_cache(self, job: AgentJob) -> dict[str, str] | None:
		"""
		Fetch live output from cache during an ongoing clone job.
		Falls back to early failure parsing if no cache output found.
		"""
		clone_step = self._get_clone_step(job)
		if not clone_step:
			return None

		cached = frappe.cache.hget("agent_job_step_output", clone_step)
		if not cached:
			return None

		try:
			output = json.loads(cached)
		except json.JSONDecodeError:
			return None

		# Refer to agent/builder.py for output structure, [pre-build]
		pre_build = output.get("pre-build", [])
		if not pre_build:
			return None

		return self._parse_app_output_map(pre_build)

	def _get_output_from_db(self, job: AgentJob) -> dict[str, str] | None:
		"""Get job output from DB for terminal clone steps"""
		clone_step = self._get_clone_step(job)
		if not clone_step:
			return None

		stored_output = frappe.db.get_value("Agent Job Step", clone_step, "data")
		if not stored_output:
			return None

		try:
			output = json.loads(stored_output)
		except json.JSONDecodeError:
			return None

		return self._parse_app_output_map(output)

	def _ensure_previous_steps_are_updated(
		self, non_terminal_clone_steps: list[DeployCandidateBuildStep], failed_step: DeployCandidateBuildStep
	):
		"""In case a step fails and we haven't update previous steps states.
		Due to cache publish issues ensure we mark them as success before marking the failed step as failure.
		"""
		failed_index = non_terminal_clone_steps.index(failed_step)
		for step in non_terminal_clone_steps[:failed_index]:
			# We know for sure these steps succeeded since the job continued
			# However since they were quick there is a chance cache output does not exist yet.
			if step.status != "Success":
				step.status = "Success"
				step.save()

	def _update_clone_steps(
		self, non_terminal_clone_steps: list[DeployCandidateBuildStep], app_output_map: dict[str, str]
	) -> bool:
		"""Update clone steps with parsed output. Returns True if any step failed."""
		clone_failed = False
		for step in non_terminal_clone_steps:
			entry = app_output_map.get(step.step_slug)
			if not entry:
				continue

			first_line = entry.splitlines()[0] if entry else ""
			step.cached = "CACHED" in first_line
			step.status = "Failure" if "Failed to clone repository" in entry else "Success"
			step.output = entry
			step.save()

			if step.status == "Failure":
				self._ensure_previous_steps_are_updated(non_terminal_clone_steps, failed_step=step)
				clone_failed = True

		return clone_failed

	def _get_app_output_map(self, job: AgentJob, non_terminal_clone_steps: list) -> dict[str, str]:
		"""
		Fetch app output from failure, cache then DB in that order.
		Cache is preferred unless this is the last step, since the last step
		may not have published to cache before the job completed.
		"""
		output = self._parse_failed_output(job)
		if output:
			return output

		is_last_step = len(non_terminal_clone_steps) == 1
		if not is_last_step:
			app_output_map = self._get_output_from_cache(job)
			if app_output_map:
				return app_output_map

		return self._get_output_from_db(job) or {}

	def parse_clone_output_and_update_step(self, job: AgentJob) -> bool:
		"""
		Parse clone output and update corresponding clone steps.
		Returns True if any clone step failed.
		"""
		if self.dcb.has_failed_clone_steps():
			return True

		non_terminal_clone_steps = self.dcb.get_all_pending_clone_steps()
		if not non_terminal_clone_steps:
			return False

		app_output_map = self._get_app_output_map(job, non_terminal_clone_steps)
		if not app_output_map:
			return False

		return self._update_clone_steps(non_terminal_clone_steps, app_output_map)


class UploadStepUpdater:
	"""
	Processes the output of `client.images.push` and uses it to update
	the last `build_step` which pertains to uploading the image to the
	registry.

	Similar to DockerBuildOutputParser, this can process the output from
	a remote (agent) or local (press) builder docker push.
	"""

	_upload_step: "DeployCandidateBuildStep | None"

	def __init__(self, dc: "DeployCandidateBuild") -> None:
		self.dc = dc
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
			self._update_output(line)

		last_update = self.dc.last_updated
		duration = (now_datetime() - last_update).total_seconds()
		self.upload_step.duration = rounded(duration, 1)
		self.flush_output()

	def end(self, status: Literal["Success", "Failure"] | None):
		if not self.upload_step:
			return

		# Used only if the build is running locally
		self.upload_step.status = status
		self.flush_output()

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
