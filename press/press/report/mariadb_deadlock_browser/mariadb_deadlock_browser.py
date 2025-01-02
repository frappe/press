# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING

import frappe
from elasticsearch import Elasticsearch
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import get_datetime
from frappe.utils.password import get_decrypted_password

if TYPE_CHECKING:
	from datetime import datetime


def fetch_mariadb_error_logs(
	site: str, start_datetime: datetime, end_datetime: datetime, log_size: int
) -> list[tuple[str, str]]:
	server = frappe.get_value("Site", site, "server")
	database_server = frappe.get_value("Server", server, "database_server")
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return []

	query = {
		"bool": {
			"filter": [
				{
					"bool": {
						"filter": [
							{
								"bool": {
									"minimum_should_match": 1,
									"should": [{"term": {"host.name": {"value": database_server}}}],
								}
							},
							{
								"bool": {
									"minimum_should_match": 1,
									"should": [{"term": {"event.dataset": {"value": "mysql.error"}}}],
								}
							},
							{
								"bool": {
									"minimum_should_match": 1,
									"should": [{"term": {"log.level": {"value": "Note"}}}],
								}
							},
							{
								"bool": {
									"minimum_should_match": 1,
									"should": [{"match_phrase": {"message": "InnoDB:"}}],
								}
							},
						]
					}
				},
				{
					"range": {
						"@timestamp": {
							"gte": int(start_datetime.timestamp() * 1000),
							"lte": int(end_datetime.timestamp() * 1000),
						}
					}
				},
			],
			"must": [],
			"must_not": [],
			"should": [],
		}
	}

	url = f"https://{log_server}/elasticsearch/"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")
	client = Elasticsearch(url, basic_auth=("frappe", password))

	data = client.search(
		size=log_size,
		index="filebeat-*",
		query=query,
	)

	if not data:
		return []

	# prepare logs
	log_map = {}
	log_timestamp = {}

	for record in data.get("hits", {}).get("hits", []):
		if record["_source"]["mysql"] and record["_source"]["mysql"]["thread_id"]:
			thread_id = record["_source"]["mysql"]["thread_id"]
			if thread_id not in log_map:
				log_map[thread_id] = []
				log_timestamp[thread_id] = record["_source"]["@timestamp"]
			# Strip `InnoDB: ` -> 8 characters
			log_map[thread_id].append((record["_source"]["log"]["offset"], record["_source"]["message"][8:]))

	# merge logs
	logs = []  # list of tuples (timestamp, log)

	for thread_id in log_map:
		# sort in order of offset
		records = sorted(log_map[thread_id], key=lambda x: x[0])
		records = [x[1] for x in records]
		logs.append((log_timestamp[thread_id], "".join(records)))

	return logs


# Regex for parsing database logs
# *** (1) TRANSACTION:
transaction_pattern = re.compile(r"^\*\*\* \(\d+\) TRANSACTION:")
# TRANSACTION 988653582, ACTIVE 6 sec starting index read
transaction_id_pattern = re.compile(r"TRANSACTION (\d+),")
query_pattern = re.compile(r"MariaDB thread id .*\n([\s\S]*)\*\*\* WAITING FOR THIS LOCK TO BE GRANTED")
actual_transaction_pattern = re.compile(r"\*\*\* WAITING FOR THIS LOCK TO BE GRANTED:\nRECORD LOCKS (.*)\n")
conflicted_transaction_pattern = re.compile(r"\*\*\* CONFLICTING WITH:\nRECORD LOCKS (.*)\n")
trx_id_pattern = re.compile(r"trx id (\d+)")
db_table_pattern = re.compile(r"table `([^`]+)`.`([^`]+)`")


class DatabaseTransactionLog:
	@staticmethod
	def parse(data: str, database: str):
		transaction_info = actual_transaction_pattern.search(data).group(1)
		found_database = db_table_pattern.search(transaction_info).group(1)
		if database != found_database:
			return None

		return DatabaseTransactionLog(data)

	def __init__(self, data: str):
		self.transaction_id = transaction_id_pattern.search(data).group(1)
		actual_transaction_info = actual_transaction_pattern.search(data).group(1)
		db_table_info = db_table_pattern.search(actual_transaction_info)
		self.database = db_table_info.group(1)
		self.table = db_table_info.group(2)
		self.query = query_pattern.search(data).group(1)

		conflicted_transaction_info = conflicted_transaction_pattern.search(data).group(1)
		self.conflicted_transaction_id = trx_id_pattern.search(conflicted_transaction_info).group(1)
		conflicted_db_table = db_table_pattern.search(conflicted_transaction_info)
		self.conflicted_table = conflicted_db_table.group(2)


def parse_log(log: str, database: str) -> list[DatabaseTransactionLog]:
	log_lines = log.split("\n")
	log_lines = [line.strip() for line in log_lines]
	log_lines = [line for line in log_lines if line != ""]
	transactions_content = []

	started_transaction_index = None
	for index, line in enumerate(log_lines):
		if transaction_pattern.match(line):
			if started_transaction_index is not None:
				transactions_content.append("\n".join(log_lines[started_transaction_index:index]))
			started_transaction_index = index

	if started_transaction_index is not None:
		transactions_content.append("\n".join(log_lines[started_transaction_index:]))

	transactions = []
	for transaction_content in transactions_content:
		with contextlib.suppress(Exception):
			trx = DatabaseTransactionLog.parse(transaction_content, database)
			if trx is not None:
				transactions.append(trx)

	return transactions


def deadlock_summary(transactions: list[DatabaseTransactionLog]) -> list[dict]:
	transaction_map: dict[str, DatabaseTransactionLog] = {}
	for transaction in transactions:
		transaction_map[transaction.transaction_id] = transaction

	deadlock_transaction_ids = {}

	for transaction in transactions:
		# usually if there is a deadlock, there will be two records
		# one record for deadlock of query A due to query B
		# and another record for deadlock of query B due to query A
		# so, we want to record only one instance of deadlock
		if (
			transaction.conflicted_transaction_id
			and (
				transaction.conflicted_transaction_id not in deadlock_transaction_ids
				or deadlock_transaction_ids[transaction.conflicted_transaction_id]
				!= transaction.transaction_id
			)
			and transaction.transaction_id != transaction.conflicted_transaction_id
		):
			deadlock_transaction_ids[transaction.transaction_id] = transaction.conflicted_transaction_id

	deadlock_infos = []
	for transaction_id in deadlock_transaction_ids:
		if transaction_id not in transaction_map:
			continue
		if transaction.conflicted_transaction_id not in transaction_map:
			continue
		transaction = transaction_map[transaction_id]
		conflicted_transaction = transaction_map[transaction.conflicted_transaction_id]
		deadlock_infos.append(
			{
				"txn_id": transaction.transaction_id,
				"table": transaction.table,
				"conflicted_txn_id": transaction.conflicted_transaction_id,
				"conflicted_table": transaction.conflicted_table,
				"query": transaction.query,
				"conflicted_query": conflicted_transaction.query,
			}
		)
	return deadlock_infos


# Report
COLUMNS = [
	{
		"fieldname": "timestamp",
		"label": "Timestamp",
		"fieldtype": "Datetime",
		"width": 160,
	},
	{
		"fieldname": "table",
		"label": "Table",
		"fieldtype": "Data",
		"width": 180,
	},
	{
		"fieldname": "transaction_id",
		"label": "Transaction",
		"fieldtype": "Data",
		"width": 120,
	},
	{
		"fieldname": "query",
		"label": "Query",
		"fieldtype": "Data",
		"width": 1400,
	},
]


def execute(filters=None):
	frappe.only_for(["System Manager", "Site Manager", "Press Admin", "Press Member"])
	filters.database = frappe.db.get_value("Site", filters.site, "database_name")
	if not filters.database:
		frappe.throw(
			f"Database name not found for site {filters.site}\nRun `Sync Info` from Site doctype actions to set the database name.\nThen retry again."
		)

	make_access_log(
		doctype="Site",
		document=filters.site,
		file_type="MariaDB Deadlock Browser",
		report_name="MariaDB Deadlock Browser",
		filters=filters,
	)
	records = fetch_mariadb_error_logs(
		filters.site,
		get_datetime(filters.start_datetime),
		get_datetime(filters.stop_datetime),
		filters.max_log_size,
	)
	data = []

	for record in records:
		timestamp = record[0]
		transactions = parse_log(record[1], filters.database)
		summaries = deadlock_summary(transactions)
		for summary in summaries:
			data.append(
				{
					"timestamp": timestamp,
					"table": summary["table"],
					"transaction_id": summary["txn_id"],
					"query": summary["query"],
				}
			)
			data.append(
				{
					"timestamp": "",
					"table": summary["conflicted_table"],
					"transaction_id": summary["conflicted_txn_id"],
					"query": summary["conflicted_query"],
				}
			)
			data.append({})  # empty line to separate records

	return COLUMNS, data
