import csv
import json
import os
import re
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

monitoring_server = os.getenv("MONITORING_SERVER_BASE_URL")
monitoring_server_user = os.getenv("MONITORING_SERVER_USER")
monitoring_server_password = os.getenv("MONITORING_SERVER_PASSWORD")


class SQLiteDB:
	def __init__(self, db_path):
		self.db_path = db_path
		self.conn = None

	def __enter__(self):
		self.conn = sqlite3.connect(self.db_path)
		self.conn.execute("PRAGMA journal_mode=WAL;")
		self._ensure_table_exists()
		return self.conn

	def __exit__(self, exc_type, exc_value, traceback):
		if self.conn:
			if exc_type is None:
				self.conn.commit()
			else:
				self.conn.rollback()
			self.conn.close()

	def _ensure_table_exists(self):
		self.conn.execute("""
            CREATE TABLE IF NOT EXISTS disk_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                server TEXT,
                device TEXT,
                written_bytes INTEGER,
                read_bytes INTEGER,
                p75_iops_usage REAL,
                p90_iops_usage REAL,
                p99_iops_usage REAL
            );
        """)

		self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_disk_stats_server ON disk_stats (server);
        """)

		self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server TEXT,
                disk_size INTEGER,
                start_time INTEGER,
                duration INTEGER
            )
        """)


def fetch_disk_stats(server_name):  # noqa: C901
	url = f"{monitoring_server}/prometheus/api/v1/query_range"

	if not monitoring_server or not monitoring_server_user or not monitoring_server_password:
		raise ValueError(
			"Environment variables MONITORING_SERVER, MONITORING_SERVER_USER, and MONITORING_SERVER_PASSWORD must be set."
		)

	queries = {
		"written_bytes": f'increase(node_disk_written_bytes_total{{instance="{server_name}"}}[1h])',
		"read_bytes": f'increase(node_disk_read_bytes_total{{instance="{server_name}"}}[1h])',
		"p75_iops": f'quantile(0.75, rate(node_disk_io_time_seconds_total{{instance="{server_name}"}}[1h])) by (device)',
		"p90_iops": f'quantile(0.90, rate(node_disk_io_time_seconds_total{{instance="{server_name}"}}[1h])) by (device)',
		"p99_iops": f'quantile(0.99, rate(node_disk_io_time_seconds_total{{instance="{server_name}"}}[1h])) by (device)',
	}

	start = datetime(2025, 2, 1)  # February 1st, 2025
	end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # last day 12:00:00
	steps = 3600  # 1 hr

	results = {}

	for metric, query in queries.items():
		response = requests.get(
			url,
			params={
				"query": query,
				"start": start.timestamp(),
				"end": end.timestamp(),
				"step": str(steps),
			},
			auth=(monitoring_server_user, monitoring_server_password),
		).json()
		results[metric] = response.get("data", {}).get("result", [])

	device_data = {}

	for metric, data in results.items():
		for result in data:
			device = result.get("metric", {}).get("device", "")
			if not device:
				continue
			for value in result.get("values", []):
				timestamp = int(value[0])
				key = f"{device}-{timestamp}"
				if key not in device_data:
					device_data[key] = {
						"server": server_name,
						"device": device,
						"timestamp": timestamp,
						"written_bytes": None,
						"read_bytes": None,
						"p75_iops_usage": None,
						"p90_iops_usage": None,
						"p99_iops_usage": None,
					}
				if metric == "written_bytes":
					device_data[key]["written_bytes"] = int(float(value[1]))
				elif metric == "read_bytes":
					device_data[key]["read_bytes"] = int(float(value[1]))
				elif metric == "p75_iops":
					device_data[key]["p75_iops_usage"] = round(float(value[1]) * 100, 2)
				elif metric == "p90_iops":
					device_data[key]["p90_iops_usage"] = round(float(value[1]) * 100, 2)
				elif metric == "p99_iops":
					device_data[key]["p99_iops_usage"] = round(float(value[1]) * 100, 2)

	with SQLiteDB("database.db") as conn:
		cursor = conn.cursor()
		# Drop all existing data of the server
		cursor.execute("delete from disk_stats WHERE server = ?", (server_name,))
		for device_info in device_data.values():
			cursor.execute(
				"""
                insert into disk_stats (timestamp, server, device, written_bytes, read_bytes, p75_iops_usage, p90_iops_usage, p99_iops_usage)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
				(
					device_info["timestamp"],
					device_info["server"],
					device_info["device"],
					device_info["written_bytes"],
					device_info["read_bytes"],
					device_info["p75_iops_usage"],
					device_info["p90_iops_usage"],
					device_info["p99_iops_usage"],
				),
			)


def fetch_all_disk_stats():
	if not os.path.exists("servers.json"):
		raise FileNotFoundError("servers.json file not found. Please create it with server names")

	with open("servers.json") as f:
		servers = json.load(f)

	fetched_count = 0
	for server in servers:
		print(
			f"\rTotal - {len(servers)} | Current - {fetched_count} | Currently fetching {server}\r",
			end="",
		)
		try:
			fetch_disk_stats(server)
			fetched_count += 1
			time.sleep(0.1)
		except Exception as e:
			print(f"Error fetching stats for {server}: {e}")

	print(f"\nFetched stats for {fetched_count} out of {len(servers)} servers.")


def feed_snapshot_details():
	"""
	Export atleast these columns
	- Virtual Machine
	- Size
	- Start Time
	- Duration
	"""
	if not os.path.exists("snapshot.csv"):
		raise FileNotFoundError("snapshot.csv file not found. Please create it with snapshot details")

	with open("snapshot.csv") as f:
		reader = csv.reader(f)
		# Figure out the header row
		header = next(reader)
		# Find index of Virtual Machine, Size, Start Time, Duration
		vm_index = header.index("Virtual Machine")
		size_index = header.index("Size")
		start_time_index = header.index("Start Time")
		duration_index = header.index("Duration")

		with SQLiteDB("database.db") as conn:
			cursor = conn.cursor()
			cursor.execute("DELETE FROM snapshots")
			for row in reader:
				# Process each row and feed the data
				virtual_machine = row[vm_index]
				size = int(row[size_index]) * 1024 * 1024 * 1024  # Convert GB to bytes

				start_time = int(
					datetime.strptime(row[start_time_index], "%Y-%m-%d %H:%M:%S")
					.replace(tzinfo=timezone.utc)
					.timestamp()
				)
				duration = parse_duration_to_seconds(row[duration_index])

				cursor.execute(
					"""
                    INSERT INTO snapshots (server, disk_size, start_time, duration)
                    VALUES (?, ?, ?, ?)
                    """,
					(virtual_machine, size, start_time, duration),
				)


def parse_duration_to_seconds(duration_str: str) -> int:
	"""
	Parse duration string like "8h 34m 39s" to total seconds
	"""
	# Remove any extra spaces and convert to lowercase
	duration_str = duration_str.strip().lower()

	# Initialize total seconds
	total_seconds = 0

	# Extract hours, minutes, and seconds using regex
	hours_match = re.search(r"(\d+)h", duration_str)
	minutes_match = re.search(r"(\d+)m", duration_str)
	seconds_match = re.search(r"(\d+)s", duration_str)

	if hours_match:
		total_seconds += int(hours_match.group(1)) * 3600
	if minutes_match:
		total_seconds += int(minutes_match.group(1)) * 60
	if seconds_match:
		total_seconds += int(seconds_match.group(1))

	return total_seconds


def safe_min(vals):
	return min(vals) if vals else None


def safe_max(vals):
	return max(vals) if vals else None


def safe_avg(vals):
	return sum(vals) / len(vals) if vals else None


def build_dataset():
	with SQLiteDB("database.db") as conn:
		cursor = conn.cursor()

		# Step 1: Get all filtered snapshots for the server
		cursor.execute("""
            SELECT id, server, start_time, duration, disk_size
            FROM snapshots
            WHERE disk_size >= 11 * 1024 * 1024 * 1024
            ORDER BY server, start_time
        """)
		all_snapshots = cursor.fetchall()

		# Step 2: Group by server and build previous snapshot logic
		snapshots_by_server = defaultdict(list)
		for snap in all_snapshots:
			snapshots_by_server[snap[1]].append(snap)  # snap[1] = server

		results = []

		for server, snaps in snapshots_by_server.items():
			for i in range(1, len(snaps)):
				curr = snaps[i]
				prev = None

				# Look for latest fully completed previous snapshot
				for j in range(i - 1, -1, -1):
					candidate = snaps[j]
					candidate_end = candidate[2] + candidate[3]  # start_time + duration
					if candidate_end <= curr[2]:  # candidate ends before current starts
						prev = candidate
						break

				if not prev:
					continue  # no valid previous snapshot

				curr_id, _, start, duration, size = curr
				_, _, prev_start, _, prev_size = prev

				# Step 3: Query disk_stats for this window
				cursor.execute(
					"""
                    SELECT p75_iops_usage, p90_iops_usage, p99_iops_usage
                    FROM disk_stats
                    WHERE server = ?
                    AND timestamp >= ?
                    AND timestamp < ?
                """,
					(server, prev_start, start),
				)
				rows = cursor.fetchall()

				p75_vals = [r[0] for r in rows if r[0] is not None]
				p90_vals = [r[1] for r in rows if r[1] is not None]
				p99_vals = [r[2] for r in rows if r[2] is not None]

				# Step 4: Total read/write
				cursor.execute(
					"""
                    SELECT SUM(written_bytes), SUM(read_bytes)
                    FROM disk_stats
                    WHERE server = ?
                    AND timestamp >= ?
                    AND timestamp < ?
                """,
					(server, prev_start, start),
				)
				writes, reads = cursor.fetchone()
				writes = writes or 0
				reads = reads or 0

				if writes == 0 or reads == 0 or not p75_vals or not p90_vals or not p99_vals:
					continue

				results.append(
					{
						"server": server,
						"timestamp": start,
						"snapshot_size_diff": abs(size - prev_size),
						"total_writes": writes,
						"total_reads": reads,
						"min_p75_iops": safe_min(p75_vals),
						"avg_p75_iops": safe_avg(p75_vals),
						"max_p75_iops": safe_max(p75_vals),
						"min_p90_iops": safe_min(p90_vals),
						"avg_p90_iops": safe_avg(p90_vals),
						"max_p90_iops": safe_max(p90_vals),
						"min_p99_iops": safe_min(p99_vals),
						"avg_p99_iops": safe_avg(p99_vals),
						"max_p99_iops": safe_max(p99_vals),
						"duration": duration,
					}
				)

		print(f"Exporting {len(results)} valid records to merged_data.json")
		with open("merged_data.json", "w") as f:
			json.dump(results, f, indent=4)


def build_model():
	import joblib
	import numpy as np
	import pandas as pd
	from sklearn.ensemble import RandomForestRegressor
	from sklearn.metrics import mean_squared_error, r2_score
	from sklearn.model_selection import train_test_split

	with open("merged_data.json", "r") as f:
		df = pd.read_json(f)

	# Define max duration threshold (5 hours in seconds)
	max_duration = 5 * 3600  # 18000 seconds

	# Filter out rows where duration > 5 hours
	df_filtered = df[df["duration"] <= max_duration].copy()

	# Prepare features and target
	features = ["total_writes", "max_p99_iops"]
	X = df_filtered[features]
	X.loc[:, "total_writes"] = X["total_writes"] / (1024 * 1024 * 1024)
	y = df_filtered["duration"]

	# Split data into train and test set
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

	# Initialize and train Random Forest Regressor
	rf = RandomForestRegressor(n_estimators=25, random_state=42)
	rf.fit(X_train, y_train)

	# Predict on test set
	y_pred = rf.predict(X_test)

	# Calculate performance metrics
	r2 = r2_score(y_test, y_pred)
	rmse = np.sqrt(mean_squared_error(y_test, y_pred))
	print(f"R² Score: {r2:.4f}")
	print(f"RMSE: {rmse:.2f}")

	joblib.dump(rf, "snapshot_time_estimator.pkl", compress=3)
