import os
import platform
import random
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Tuple, TypedDict

CommandOutput = TypedDict(
	"CommandOutput",
	cwd=str,
	image_tag=str,
	returncode=int,
	output=str,
)


def copy_file_from_docker_cache(
	container_source: str,
	host_dest: str = ".",
	cache_target: str = "/home/frappe/.cache",
):
	"""
	Function is used to copy files from docker cache i.e. `cache_target/container_source`
	to the host system i.e `host_dest`.

	This function is required cause cache files may be available only during docker build.

	This works by:
	- copy the file from mount cache (image) to another_folder (image)
	- create a container from image
	- copy file from another_folder (container) to host system (using docker cp)
	- remove container and then image
	"""
	filename = Path(container_source).name
	container_dest_dirpath = Path(cache_target).parent / "container_dest"
	container_dest_filepath = container_dest_dirpath / filename
	command = (
		f"mkdir -p {container_dest_dirpath} && "
		+ f"cp {container_source} {container_dest_filepath}"
	)
	output = run_command_in_docker_cache(
		command,
		cache_target,
		False,
	)

	if output["returncode"] == 0:
		container_id = create_container(output["image_tag"])
		copy_file_from_container(
			container_id,
			container_dest_filepath,
			Path(host_dest),
		)
		remove_container(container_id)

	run_image_rm(output["image_tag"])
	return output


def run_command_in_docker_cache(
	command: str = "ls -A",
	cache_target: str = "/home/frappe/.cache",
	remove_image: bool = True,
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
	output = run_build_command(df_path, remove_image)
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


def create_container(image_tag: str) -> str:
	args = shlex.split(f"docker create --platform linux/amd64 {image_tag}")
	return subprocess.run(
		args,
		env=os.environ.copy(),
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	).stdout.strip()


def copy_file_from_container(
	container_id: str,
	container_filepath: Path,
	host_dest: Path,
):
	container_source = f"{container_id}:{container_filepath}"
	args = ["docker", "cp", container_source, host_dest.as_posix()]
	proc = subprocess.run(
		args,
		env=os.environ.copy(),
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)

	if not proc.returncode:
		print(
			f"file copied:\n"
			f"- from {container_source}\n"
			f"- to   {host_dest.absolute().as_posix()}"
		)
	else:
		print(proc.stdout)


def remove_container(container_id: str) -> str:
	args = shlex.split(f"docker rm -v {container_id}")
	subprocess.run(
		args,
		env=os.environ.copy(),
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	).stdout


def prep_dockerfile_path(dockerfile: str) -> Path:
	dir = Path("cache_check_dockerfile_dir")
	if dir.is_dir():
		shutil.rmtree(dir)

	dir.mkdir()
	df_path = dir / "Dockerfile"
	with open(df_path, "w") as df:
		df.write(dockerfile)

	return df_path


def run_build_command(df_path: Path, remove_image: bool) -> CommandOutput:
	command, image_tag = get_cache_check_build_command()
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
	if remove_image:
		run_image_rm(image_tag)
	return dict(
		cwd=df_path.parent.absolute().as_posix(),
		image_tag=image_tag,
		returncode=output.returncode,
		output=strip_build_output(output.stdout),
	)


def get_cache_check_build_command() -> Tuple[str, str]:
	command = "docker build"
	if (
		platform.machine() == "arm64"
		and platform.system() == "Darwin"
		and platform.processor() == "arm"
	):
		command += "x build --platform linux/amd64"

	now_ts = datetime.timestamp(datetime.today())
	command += f" --build-arg CACHE_BUST={now_ts}"

	image_tag = f"cache_check:id-{random.getrandbits(40):x}"
	command += f" --tag {image_tag} ."
	return command, image_tag


def run_image_rm(image_tag: str):
	command = f"docker image rm {image_tag}"
	subprocess.run(
		shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
	)


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
