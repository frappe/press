from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TableUsage:
	table: str = field(init=False)
	filename: str
	data_length: int
	index_length: int
	data_free: int
	engine: Literal["InnoDB", "MyISAM"]

	def __post_init__(self) -> None:
		name, _ = os.path.splitext(os.path.basename(self.filename))
		self.table = str(name).replace("@0020", " ")


@dataclass
class Usage:
	data_length: int
	index_length: int
	data_free: int
	tables: list[TableUsage]


def usage(
	database: str,
	table: str | None = None,
	excluded_tables: list[str] | None = None,
	engine: Literal["InnoDB", "MyISAM"] | None = None,
	*,
	base_path: str = "/var/lib/mysql/",
	io_wait_threshold: float = 50.0,
	io_ops_limit: float = 200.0,
	concurrency: int = 20,
	use_sudo: bool = True,
) -> Usage:
	"""
	Calculate table usage statistics for a MariaDB database.

	Args:
		database (str): Name of the database.
		table (str | None): Specific table to query. If None, all tables are queried
			in the database.
		excluded_tables (list[str] | None): List of table names to exclude from the
			analysis. You can pass regex patterns as well.
		engine (Literal["InnoDB", "MyISAM"] | None): Storage engine of the table. Must be
			specified if querying a single table.
		base_path (str): Base path to the MariaDB data directory. Defaults to /var/lib/mysql/.
		io_wait_threshold (float): I/O wait threshold percentage. Parsing and usage calculation will be halted,
			if the system cpu iowait exceeds this threshold.
		io_ops_limit (float): Max IO operations per second. Defaults to 200.
		concurrency (int): Number of parallel threads to use.
			For a specific table, at a time we will read one page at max.
			1 InnoDB page = 16KB. If the block size is 4KB, then 4 reads will be done in parallel.
			So, set this value accordingly, so that it does not overwhelm the disk I/O and also utilize the disk optimally.
		use_sudo (bool): Whether to run the command with sudo.

	Returns:
		Usage: Usage statistics including per-table details.
	"""
	if excluded_tables is None:
		excluded_tables = []

	if table and not engine:
		raise ValueError("Engine must be specified when querying a single table.")

	mariadb_table_usage_executable = os.path.join(
		os.path.dirname(os.path.abspath(__file__)), "lib", "mariadb_table_usage"
	)

	command = [
		mariadb_table_usage_executable,
		f"--io-wait-threshold={io_wait_threshold}",
		f"--io-ops-limit={io_ops_limit}",
		f"--parallel={concurrency}",
	]

	for tbl in excluded_tables:
		tbl_formatted = tbl.strip().replace(" ", "@0020")
		command.append(f"--exclude={tbl_formatted}")

	path = os.path.join(base_path, database)
	if table:
		path = os.path.join(path, table + (".ibd" if engine == "InnoDB" else ".MYD"))

	command.append(path)

	# Run the command and capture output
	if use_sudo:
		command.insert(0, "sudo")

	result = subprocess.run(command, capture_output=True, text=True, check=False)
	if result.returncode != 0:
		raise RuntimeError("Error running mariadb_table_usage: " + result.stderr)

	output = result.stdout.strip()
	data: list[dict] = json.loads(output)

	res = Usage(
		tables=[TableUsage(**entry) for entry in data],
		data_length=0,
		index_length=0,
		data_free=0,
	)
	res.data_length = sum(tbl.data_length for tbl in res.tables)
	res.index_length = sum(tbl.index_length for tbl in res.tables)
	res.data_free = sum(tbl.data_free for tbl in res.tables)

	return res


__all__ = ["usage"]
