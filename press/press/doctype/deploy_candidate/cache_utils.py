import os
import platform
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import TypedDict

CommandOutput = TypedDict(
	"CommandOutput",
	returncode=int,
	output=str,
)


def run_command_in_docker_cache(
	command: str = "ls -A",
	cache_target: str = "/home/frappe/.cache",
) -> CommandOutput:
	"""
	This function works by capturing the output of the given `command`
	by running it in the cache dir (`cache_target`) while building a
	dummy image.

	The primary purpose is to check the contents of the mounted cache. It's
	an incredibly hacky way to achieve this, but afaik the only one.

	Note: The `ARG CACHE_BUST=1` line is used to cause layer cache miss
	while running `command` at `cache_target`. This is achieved by changing
	`CACHE_BUST` value every run.

	Warning: Takes time to run, use judiciously.
	"""
	dockerfile = get_cache_check_dockerfile(
		command,
		cache_target,
	)
	df_path = prep_dockerfile_path(dockerfile)
	output = run_build_command(df_path)
	shutil.rmtree(df_path.parent)
	return output


def get_cache_check_dockerfile(command: str, cache_target: str) -> str:
	"""
	Note: Mount cache is identified by different attributes, hence it should
	be the same as the Dockerfile else it will always result in a cache miss.

	Ref: https://docs.docker.com/engine/reference/builder/#run---mounttypecache
	"""
	df = f"""
		FROM ubuntu:20.04
		ARG CACHE_BUST=1
		WORKDIR {cache_target}
		RUN --mount=type=cache,target={cache_target},uid=1000,gid=1000 {command}
	"""
	return dedent(df).strip()


def prep_dockerfile_path(dockerfile: str) -> Path:
	dir = Path("cache_check_dockerfile_dir")
	if dir.is_dir():
		shutil.rmtree(dir)

	dir.mkdir()
	df_path = dir / "Dockerfile"
	with open(df_path, "w") as df:
		df.write(dockerfile)

	return df_path


def run_build_command(df_path: Path) -> CommandOutput:
	command = get_cache_check_build_command()
	env = os.environ.copy()
	env["DOCKER_BUILDKIT"] = "1"
	env["BUILDKIT_PROGRESS"] = "plain"

	output = subprocess.run(
		shlex.split(command),
		env=env,
		cwd=df_path.parent,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)
	return dict(returncode=output.returncode, output=strip_build_output(output.stdout))


def get_cache_check_build_command() -> str:
	command = "docker build"
	if (
		platform.machine() == "arm64"
		and platform.system() == "Darwin"
		and platform.processor() == "arm"
	):
		command += "x build --platform linux/amd64"

	now_ts = datetime.timestamp(datetime.today())
	command += f" --build-arg CACHE_BUST={now_ts} ."
	return command


def strip_build_output(stdout: str) -> str:
	output = []
	is_output = False

	line_rx = re.compile(r"^#\d+\s\d+\.\d+\s")
	done_rx = re.compile(r"^#\d+\sDONE\s\d+\.\d+s$")

	for line in stdout.split("\n"):
		if is_output and (m := line_rx.match(line)):
			start = m.end()
			output.append(line[start:])
		elif is_output and done_rx.search(line):
			break
		elif "--mount=type=cache,target=" in line:
			is_output = True
	return "\n".join(output)


def get_cached_apps() -> dict[str, list[str]]:
	result = run_command_in_docker_cache(
		command="ls -A bench/apps",
		cache_target="/home/frappe/.cache",
	)

	apps = dict()
	if result["returncode"] != 0:
		return apps

	for line in result["output"].split("\n"):
		# File Name: app_name-cache_key.ext
		splits = line.split("-", 1)
		if len(splits) != 2:
			continue

		app_name, suffix = splits
		suffix_splits = suffix.split(".", 1)
		if len(suffix_splits) != 2 or suffix_splits[1] not in ["tar", "tgz"]:
			continue

		if app_name not in apps:
			apps[app_name] = []

		app_hash = suffix_splits[0]
		apps[app_name].append(app_hash)
	return apps
