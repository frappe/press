from __future__ import annotations

import contextlib
import math
import os
import subprocess
import traceback
from typing import Literal

import duckdb
import filelock

QUERY_TYPES = Literal["SELECT", "INSERT", "UPDATE", "DELETE", "OTHER"]


class Indexer:
	def __init__(
		self,
		base_path: str,
		db_name: str,
	):
		self.indexer_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "indexer")
		self.base_path = base_path
		self.db_name = db_name
		self.logging = False
		self._lock_file_path = os.path.join(self.base_path, "indexer.lock")

	def add(self, binlog_path: str, batch_size: int = 10000):
		with filelock.FileLock(self._lock_file_path):
			subprocess.run(
				[
					self.indexer_lib,
					"add",
					self.base_path,
					binlog_path,
					self.db_name,
					str(batch_size),
				]
			)

	def remove(self, binlog_path: str):
		with filelock.FileLock(self._lock_file_path):
			subprocess.run([self.indexer_lib, "remove", self.base_path, binlog_path, self.db_name])

	def get_timeline(
		self,
		start_timestamp: int,
		end_timestamp: int,
		type: QUERY_TYPES | None = None,
		database: str | None = None,
	):
		"""
		Args:
			start_timestamp: The start timestamp in seconds UTC
			end_timestamp: The end timestamp in seconds UTC
			type: The query type to filter (SELECT, INSERT, UPDATE, DELETE, OTHER)
			database: The database name to filter (Optional)

			Note:
				start_timestamp and end_timestamp will be rounded to the nearest minute
				In case of start_timestamp, it's the floor of the rounded value
				In case of end_timestamp, it's the ceil of the rounded value

				Also, difference between end_timestamp and start_timestamp should be at least 1 minute

		Returns:
			A dictionary of timeline information
			Example:
				{
					"start_timestamp": 1677721600, // start timestamp in seconds UTC
					"end_timestamp": 1677721660, // end timestamp in seconds UTC
					"interval": 60, // interval in seconds
					"results": {
						"1677721600:1677721660": {
							"SELECT": 100, // events count
							"INSERT": 100, // events count
							"UPDATE": 100, // events count
							"DELETE": 100, // events count
						}
					},
					"tables": ["test_table"], // list of tables appeared during the time range
				}
		"""

		# Timestamp are in seconds
		# Move start_timestamp to nearest minute
		start_timestamp = math.floor(start_timestamp / 60) * 60
		# Move end_timestamp to next nearest minute
		end_timestamp = math.ceil(end_timestamp / 60) * 60

		# If the time range is less than 1 minute, set it to 1 minute
		if end_timestamp - start_timestamp < 60:
			end_timestamp = start_timestamp + 60

		# Split the time range in 30 slices
		interval = math.ceil(((end_timestamp - start_timestamp) // 30) / 60) * 60
		where_clause = ""
		parameters = [interval, start_timestamp, end_timestamp, interval]

		if type is not None:
			where_clause += " AND q.type = ? "
			parameters.append(type)

		if database is not None:
			where_clause += " AND q.db_name = ? "
			parameters.append(database)

		query_result = self._execute_query(
			"db",
			f"""WITH time_intervals AS (
				SELECT
					generate_series AS start_ts,
					generate_series + ? AS end_ts
				FROM GENERATE_SERIES(?, ?, ?)
			)
			SELECT
				t.start_ts,
				t.end_ts,
				q.type,
				COUNT(q.type) AS events_count
			FROM time_intervals t
			JOIN query q
				ON q.timestamp >= t.start_ts
				AND q.timestamp < t.end_ts
				{where_clause}
			GROUP BY t.start_ts, t.end_ts, q.type
			ORDER BY t.start_ts, q.type;""",
			parameters,
		)

		result_map = {}
		for row in query_result:
			key = f"{row[0]}:{row[1]}"
			if key not in result_map:
				result_map[key] = {}

			result_map[key][row[2]] = row[3]

		return {
			"start_timestamp": start_timestamp,
			"end_timestamp": end_timestamp,
			"interval": interval,
			"results": result_map,
			"tables": self._get_tables(database, start_timestamp, end_timestamp),
		}

	def get_row_ids(  # noqa: C901
		self,
		start_timestamp: int,
		end_timestamp: int,
		type: QUERY_TYPES | None = None,
		database: str | None = None,
		table: str | None = None,
		search_str: str | None = None,
	) -> dict[str, list[int]]:
		"""
		Args:
			start_timestamp: The start timestamp in seconds UTC
			end_timestamp: The end timestamp in seconds UTC
			type: The query type to filter (SELECT, INSERT, UPDATE, DELETE, OTHER)
			database: The database name to filter (Optional)
			table: The table name to filter (Optional)
			search_str: The full text search string (Optional)

		Returns:
			A dictionary of binlog name and a list of row ids
			Example:
				{
					"binlog_1": [101, 102, 103],
					"binlog_2": [104, 105, 106],
				}
		"""
		# First fetch all the row ids
		where_clause = ""
		parameters = [start_timestamp, end_timestamp]
		if type is not None:
			where_clause += " AND type = ? "
			parameters.append(type)
		if database is not None:
			where_clause += " AND db_name = ? "
			parameters.append(database)
		if table is not None:
			where_clause += " AND table_name = ? "
			parameters.append(table)

		row_ids = [
			i
			for i in self._execute_query(
				"db",
				f"""
				SELECT
					row_id, binlog
				FROM
					query
				WHERE
					timestamp >= ?
					AND timestamp < ?
					{where_clause}
				""",
				parameters,
			)
		]

		result = {}
		for row_id, binlog in row_ids:
			if binlog not in result:
				result[binlog] = []

			result[binlog].append(row_id)

		# Now do full text search on parquet files
		if search_str:
			for binlog, row_ids in result.items():
				parquet_file_path = os.path.join(self.base_path, f"queries_{binlog}.parquet")
				if not os.path.exists(parquet_file_path):
					continue

				result[binlog] = [
					i[0]
					for i in self._execute_query(
						"parquet",
						f"SELECT id FROM '{parquet_file_path}' WHERE id IN ? AND query ILIKE '%{search_str}%'",
						[row_ids],
					)
				]

		return result

	def get_queries(
		self,
		row_ids: dict[str, list[int]],
		database: str | None = None,
	) -> dict[dict[int, str]]:
		"""
		Args:
			row_ids: A dictionary of binlog name and a list of row ids
					{
						"binlog_1": [101, 102, 103],
						"binlog_2": [104, 105, 106],
					}
			database: The database name to filter the row ids

		Returns:
			A dictionary of binlog name and a dictionary of row id and query information
			Example:
				{
					"binlog_1": {
						101: [
							"INSERT INTO `test`.`test_table` VALUES (1, 'test')", // query
							"INSERT", // type
							6788, // event_size
							"test_db", // db_name
							"test_table", // table_name
							1677721600, // timestamp
						]
					}
				}

		"""
		if database is not None:
			# Filter out the row_ids that doesn't belong to the database
			for binlog, selected_row_ids in row_ids.items():
				row_ids = [
					i[0]
					for i in self._execute_query(
						"db",
						"SELECT row_id FROM query WHERE binlog = ? AND db_name = ? AND row_id in ? order by timestamp",
						[binlog, database, selected_row_ids],
					)
				]

		# Fetch the query info
		results = {}
		for binlog, selected_row_ids in row_ids.items():
			parquet_file_path = os.path.join(self.base_path, f"queries_{binlog}.parquet")
			if not os.path.exists(parquet_file_path):
				results[binlog] = {}
				continue

			# Fetch query from parquet file
			results[binlog] = {
				i[0]: [i[1]]
				for i in self._execute_query(
					"parquet",
					f"SELECT id, query FROM '{parquet_file_path}' where id in ? limit 500",
					[selected_row_ids],
				)
			}

			# Fetch other info from db
			data = self._execute_query(
				"db",
				"""
				SELECT
					row_id,
					type,
					event_size,
					db_name,
					table_name,
					timestamp
				FROM
					query
				WHERE
					binlog = ?
					AND row_id IN ?
				""",
				[binlog, row_ids],
			)

			for row in data:
				if row[0] not in results[binlog]:
					continue
				results[binlog][row[0]].extend([row[1], row[2], row[3], row[4], row[5]])
		return results

	def _get_tables(self, database: str, start_timestamp: int, end_timestamp: int):
		return [
			x[0]
			for x in self._execute_query(
				"db",
				"SELECT distinct table_name FROM query WHERE timestamp >= ? AND timestamp <= ? AND db_name = ?",
				[start_timestamp, end_timestamp, database],
			)
			if x[0] is not None and x[0] != ""
		]

	def _execute_query(self, source: Literal["db", "parquet"], query: str, params: list[str] | None = None):
		if params is None:
			params = []
		result = []
		db: duckdb.DuckDBPyConnection | None = None
		lock: filelock.FileLock | None = None
		try:
			if source == "parquet":
				db = duckdb.connect()
			elif source == "db":
				lock = filelock.FileLock(self._lock_file_path)
				lock.acquire(timeout=5)
				db = duckdb.connect(database=os.path.join(self.base_path, self.db_name), read_only=True)
			result = db.execute(query, parameters=params).fetchall()
		except Exception as e:
			if self.logging:
				print("Error executing query: ")
				print("Query: ", query)
				print("Parameters: ", str(params))
				print("Error: ", e)
				traceback.print_exc()
		finally:
			if db is not None:
				with contextlib.suppress(Exception):
					db.close()
			if lock is not None:
				with contextlib.suppress(Exception):
					lock.release()
		return result
