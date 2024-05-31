import json

from pathlib import Path
from typing import Any, Optional, TypedDict

PackageManagers = TypedDict(
	"PackageManagers",
	{
		"repo_path": str,
		"pyproject": Optional[dict[str, Any]],
		"packagejsons": list[dict[str, Any]],
	},
)
PackageManagerFiles = dict[str, PackageManagers]


def get_package_manager_files(repo_path_map: dict[str, str]) -> PackageManagerFiles:
	# Return pyproject.toml and package.json files
	pfiles_map = {}
	for app, repo_path in repo_path_map.items():
		pfiles_map[app] = get_package_manager_files_from_repo(app, repo_path)

	return pfiles_map


def get_package_manager_files_from_repo(app: str, repo_path: str):
	pypt, pckjs = _get_package_manager_files_from_repo(
		repo_path,
		True,
	)

	pm: PackageManagers = {
		"repo_path": repo_path,
		"pyproject": None,
		"packagejsons": [],
	}

	if pypt is not None:
		pm["pyproject"] = load_pyproject(app, pypt.absolute().as_posix())

	for pckj in pckjs:
		package_json = load_package_json(
			app,
			pckj.absolute().as_posix(),
		)
		pm["packagejsons"].append(package_json)

	return pm


def _get_package_manager_files_from_repo(
	repo_path: str,
	recursive: bool,
) -> tuple[Path | None, list[Path]]:
	pyproject_toml: Optional[Path] = None
	package_jsons: list[Path] = []  # An app can have multiple

	for p in Path(repo_path).iterdir():
		if p.name == "pyproject.toml":
			pyproject_toml = p
		elif p.name == "package.json":
			package_jsons.append(p)

		if not (recursive and p.is_dir()):
			continue

		pypt, pckjs = _get_package_manager_files_from_repo(p, False)
		if pypt is not None and pyproject_toml is None:
			pyproject_toml = pypt

		package_jsons.extend(pckjs)

	return pyproject_toml, package_jsons


def load_pyproject(app: str, pyproject_path: str):
	try:
		from tomli import TOMLDecodeError, load
	except ImportError:
		from tomllib import TOMLDecodeError, load

	with open(pyproject_path, "rb") as f:
		try:
			return load(f)
		except TOMLDecodeError:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App has invalid pyproject.toml file", app) from None


def load_package_json(app: str, package_json_path: str):
	with open(package_json_path, "rb") as f:
		try:
			return json.load(f)
		except json.JSONDecodeError:
			# Do not edit without updating deploy_notifications.py
			raise Exception(
				"App has invalid package.json file", app, package_json_path
			) from None
