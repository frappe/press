import datetime
import re
from enum import Enum

import frappe


class LOG_TYPE(Enum):
	SITE = "site"
	BENCH = "bench"


def bench_log_formatter(log_entries: list) -> list:
	"""
	Formats bench logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, level, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def worker_log_formatter(log_entries: list) -> list:
	"""
	Formats worker logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		try:
			formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
				"%Y-%m-%d %H:%M:%S"
			)
		except ValueError:
			formatted_time = ""

		formatted_logs.append({"time": formatted_time, "description": description})

	return formatted_logs


def frappe_log_formatter(log_entries: list) -> list:
	"""
	Formats frappe logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, level, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def database_log_formatter(log_entries: list) -> list:
	"""
	Formats database logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, level, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def scheduler_log_formatter(log_entries: list) -> list:
	"""
	Formats scheduler logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, level, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		# TODO: formatted time goes invalid
		formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def redis_log_formatter(log_entries: list) -> list:
	"""
	Formats redis logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		_, day, month, year, time, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		formatted_time = datetime.datetime.strptime(
			f"{year}-{month}-{day} {time}", "%Y-%b-%d %H:%M:%S.%f"
		).strftime("%Y-%m-%d %H:%M:%S")

		formatted_logs.append({"time": formatted_time, "description": description})

	return formatted_logs


def web_error_log_formatter(log_entries: list) -> list:
	"""
	Formats web error logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	# Regular expression pattern to match log entries specific to web.error logs
	regex = r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4})\] \[(\d+)\] \[(\w+)\] (.*)"

	formatted_logs = []
	for entry in log_entries:
		match = re.match(regex, entry)
		if not match:
			formatted_logs.append({"description": entry})  # Unparsable entry
			continue

		# Extract groups from the match
		date, _, level, description_parts = match.groups()
		description = "".join(description_parts)

		# Format date using strftime for cnsistency (no external libraries needed)
		formatted_time = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def monitor_json_log_formatter(log_entries: list) -> list:
	"""
	Formats monitor.json logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		try:
			timestamp_key = '"timestamp":"'
			timestamp_start = entry.index(timestamp_key) + len(timestamp_key)
			timestamp_end = entry.index('"', timestamp_start)
			time = entry[timestamp_start:timestamp_end]
			formatted_time = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f").strftime(
				"%Y-%m-%d %H:%M:%S"
			)

			formatted_logs.append({"time": formatted_time, "description": entry})
		except ValueError:
			formatted_logs.append({"description": entry})

	return formatted_logs


def ipython_log_formatter(log_entries: list) -> list:
	"""
	Formats ipython logs by extracting timestamp, level, and description.

	Args:
		log_entries (list): A list of log entries, where each entry is a string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	if not log_entries:
		return []  # Return empty list if no log entries

	formatted_logs = []
	for entry in log_entries:
		date, time, level, *description_parts = entry.split(" ")
		description = " ".join(description_parts)

		formatted_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S,%f").strftime(
			"%Y-%m-%d %H:%M:%S"
		)

		formatted_logs.append({"level": level, "time": formatted_time, "description": description})

	return formatted_logs


def fallback_log_formatter(log_entries: list) -> list:
	"""
	Fallback formatter for logs that don't have a specific formatter.

	Args:
		log_entries (list): A list of log entries, where each entry is string.

	Returns:
		list: A list of dictionaries, where each dictionary represents a formatted log entry.
	"""

	formatted_logs = []
	for entry in log_entries:
		formatted_logs.append({"description": entry})

	return formatted_logs


FORMATTER_MAP = {
	"bench": bench_log_formatter,
	"worker": worker_log_formatter,
	"frappe": frappe_log_formatter,
	"ipython": ipython_log_formatter,
	"database": database_log_formatter,
	"redis-cache": redis_log_formatter,
	"redis-queue": redis_log_formatter,
	"scheduler": scheduler_log_formatter,
	"web.error": web_error_log_formatter,
	"worker.error": worker_log_formatter,
	"monitor.json": monitor_json_log_formatter,
}


@frappe.whitelist()
def get_log(log_type: LOG_TYPE, doc_name: str, log_name: str) -> list:
	MULTILINE_LOGS = ("database.log", "scheduler.log", "worker", "ipython", "frappe.log")

	log = get_raw_log(log_type, doc_name, log_name)

	log_entries = []
	for k, v in log.items():
		if k == log_name:
			if v == "":
				return []
			if log_name.startswith(MULTILINE_LOGS):
				# split line if nextline starts with timestamp
				log_entries = re.split(r"\n(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", v)
				break

			log_entries = v.strip().splitlines()
			break

	return format_log(log_name, log_entries)


def get_raw_log(log_type: LOG_TYPE, doc_name: str, log_name: str) -> list:
	if log_type == LOG_TYPE.BENCH:
		return frappe.get_doc("Bench", doc_name).get_server_log(log_name)
	if log_type == LOG_TYPE.SITE:
		return frappe.get_doc("Site", doc_name).get_server_log(log_name)
	return frappe.throw("Invalid log type")


def format_log(log_name: str, log_entries: list) -> list:
	log_key = get_log_key(log_name)
	if log_key in FORMATTER_MAP:
		return FORMATTER_MAP[log_key](log_entries)
	return fallback_log_formatter(log_entries)


def get_log_key(log_name: str) -> str:
	# if the log file has a number at the end, it's a rotated log
	# and we don't need to consider the number for formatter mapping
	if log_name[-1].isdigit():
		log_name = log_name.rsplit(".", 1)[0]

	return log_name.rsplit(".", 1)[0]
