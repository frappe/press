from __future__ import annotations


def find_db_disk_info(df_output: str) -> tuple[int, int] | None:
	"""
	> df --output=source,size,used,target | tail -n +2
	/dev/root         9982728  6428268 /
	/dev/nvme1n1p1   30297152 19780948 /opt/volumes/mariadb
	"""
	data_disk_available = False
	if "/opt/volumes/mariadb" in df_output:
		data_disk_available = True

	for line in df_output.strip().split("\n"):
		if not data_disk_available and not (
			"/dev/root" in line or "/dev/sda1" in line or "/dev/vda1" in line or "/dev/xvda1" in line
		):
			continue
		if data_disk_available and "/opt/volumes/mariadb" not in line:
			continue
		parts = line.split()
		if len(parts) < 3:
			continue
		return int(parts[1]), int(parts[2])
	return None


def parse_du_output_of_mysql_directory(du_output: str) -> dict[str, int]:  # noqa: C901
	"""
	161392	/var/lib/mysql/_cc7c51c2a5c9f230
	12M	/var/lib/mysql/ibtmp1
	140M	/var/lib/mysql/mysql
	101M	/var/lib/mysql/mysql-bin.000452
	"""
	size_info = {}
	for line in du_output.strip().split("\n"):
		size_str, path = line.split(maxsplit=1)
		size_info[path] = int(size_str)

	data = {
		"schema": {},
		"bin_log": 0,
		"slow_log": 0,
		"error_log": 0,
		"core": 0,
		"other": 0,
	}

	for path, size in size_info.items():
		if not path.startswith("/var/lib/mysql"):
			continue
		file = path[len("/var/lib/mysql/") :]  # Remove the base path
		if file.startswith("mysql-bin"):
			data["bin_log"] += size
		elif file.startswith("mysql-slow.log"):
			data["slow_log"] += size
		elif file.startswith("mysql-error.log"):
			data["error_log"] += size
		elif file in ["ibdata1", "ib_logfile0", "ibtmp1", "aria_log_control"] or file.startswith("aria_log."):
			data["core"] += size
		elif file.startswith("_") or file in ["mysql", "performance_schema", "sys", "percona"]:
			data["schema"][file] = size
		else:
			data["other"] += size
	return data
