# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe.model.document import Document
from press.press.doctype.deploy_candidate.cache_utils import run_command_in_docker_cache
from press.utils import ttl_cache


class BenchGetAppCache(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accessed: DF.Datetime | None
		app: DF.Data | None
		file_name: DF.Data | None
		is_compressed: DF.Check
		raw: DF.Code | None
		size: DF.Float
	# end: auto-generated types

	@staticmethod
	def get_data():
		data = get_app_cache_items()
		return data

	def load_from_db(self):
		db = {v.name: v for v in BenchGetAppCache.get_data()}
		return super(Document, self).__init__(db[self.name])

	def delete(self):
		run_command_in_docker_cache(f"rm bench/apps/{self.file_name}")
		get_app_cache_items.cache.invalidate()

	@staticmethod
	def clear_app_cache() -> None:
		run_command_in_docker_cache("rm bench/apps/*.tar bench/apps/*.tgz")
		get_app_cache_items.cache.invalidate()

	@staticmethod
	def clear_app_cache_by_app(app: str) -> None:
		run_command_in_docker_cache(f"rm bench/apps/{app}-*.tar bench/apps/{app}-*.tgz")
		get_app_cache_items.cache.invalidate()

	@staticmethod
	def get_list(_):
		return BenchGetAppCache.get_data()

	@staticmethod
	def get_count(_):
		data = BenchGetAppCache.get_data()
		return len(data)

	"""
	The methods below are not applicable hence no-op.
	"""

	def db_update(self):
		pass

	def db_insert(self, *args, **kwargs):
		pass

	@staticmethod
	def get_stats(args):
		return {}


"""
ttl_cache used cause checking app cache involves
building an image to execute `ls` during build time
this takes a few of seconds (mostly a minute).
"""


@ttl_cache(ttl=20)
def get_app_cache_items():

	result = run_command_in_docker_cache("ls -luAt --time-style=full-iso bench/apps")
	if result["returncode"]:
		return []

	output = result["output"]
	values = []

	"""
	# Example Output :
	total 587164
	-rw-r--r-- 1 1000 1000 251607040 2024-02-01 10:03:33.972950013 +0000 builder-13a6ece9dd.tar
	-rw-r--r-- 1 1000 1000 321587200 2024-02-01 10:01:04.109586013 +0000 hrms-84aced29ec.tar
	-rw-r--r-- 1 1000 1000  28057600 2024-02-01 10:00:11.669851002 +0000 wiki-8b369c63dd.tar
	"""

	for line in output.splitlines():
		doc = get_dict_from_ls_line(line)
		if doc is not None:
			values.append(doc)
	return values


def get_dict_from_ls_line(line: str):
	parts = [p for p in line.split(" ") if p]
	if len(parts) != 9:
		return None

	size = 0
	accessed = datetime.fromtimestamp(0)
	datestring = " ".join(parts[5:8])
	try:
		size = int(parts[4]) / 1_000_000
		accessed = datetime.fromisoformat(datestring)
	except ValueError:
		"""
		Invalid values passed above ∵ format not as expected. Use field `raw`
		to debug and fix. Erroring out will prevent clearing of cache.
		"""
		pass

	file_name = parts[-1]
	return frappe._dict(
		name=file_name.split(".", 1)[0],
		file_name=file_name,
		app=file_name.split("-")[0],
		is_compressed=file_name.endswith(".tgz"),
		size=size,
		accessed=accessed,
		raw=line,
	)
