""" Basic DB optimizer for Frappe Framework based app.

This is largely based on heuristics and known good practices for indexing.
"""

from dataclasses import dataclass
from typing import Literal

from sql_metadata import Parser


@dataclass
class DBExplain:
	# refer: https://mariadb.com/kb/en/explain/
	# Anything not explicitly encoded here is likely not supported.
	select_type: Literal["SIMPLE", "PRIMARY", "SUBQUERY", "UNION", "DERIVED"]
	table: str
	scan_type: Literal[  # What type of scan will be performed
		"ALL",  # Full table scan
		"CONST",  # Single row will be read
		"EQ_REF",  # A single row is found from *unique* index
		"REF",  # Index is used, but MIGHT hit more than 1 rows as it's non-unique
		"RANGE",  # The table will be accessed with a key over one or more value ranges.
		"INDEX_MERGE",  # multiple indexes are used and merged smartly. Equivalent to RANGE
		"INDEX_SUBQUERY",
		"INDEX",  # Full index scan is performed. Similar to full table scan in case of large number of rows.
		"REF_OR_NULL",
		"UNIQUE_SUBQUERY",
		"FULLTEXT",  # Full text index is used,
	]
	possible_keys: list[str] | None = None  # possible indexes that can be used
	key: str | None = None  # This index is being used
	key_len: int | None = None  # How many prefix bytes from index are being used
	ref: str | None = None  # is reference constant or some other column
	rows: int = 0  # roughly how many rows will be examined
	extra: str | None = None
	parsed_query: Parser = None


@dataclass
class DBOptimizer:
	query: str  # raw query in string format
	explain_plan: list[DBExplain] = None

	def __post_init__(self):
		if not self.explain_plan:
			self.explain_plan = []
		for explain_entry in self.explain_plan:
			explain_entry.select_type = explain_entry.select_type.upper()
			explain_entry.scan_type = explain_entry.scan_type.upper()
		self.parsed_query = Parser(self.query)

	def tables_examined(self):
		return self.parsed_query.tables

	@property
	def potential_indexes(self) -> list[str]:
		"""Get all columns that can potentially be indexed to speed up this query."""

		possible_indexes = []

		# Where claus columns using these operators benefit from index
		#  1. = (equality)
		#  2. >, <, >=, <=
		#  3. LIKE 'xyz%' (Prefix search)
		#  4. BETWEEN (for date[time] fields)
		#  5. IN (similar to equality)
		if where_columns := self.parsed_query.columns_dict.get("where"):
			# TODO: Apply some heuristics here, not all columns in where clause are actually useful
			possible_indexes.extend(where_columns)

		# Join clauses - Both sides of join should ideally be indexed. One will *usually* be primary key.
		if join_columns := self.parsed_query.columns_dict.get("join"):
			possible_indexes.extend(join_columns)

		# Top N query variant - Order by column can possibly speed up the query
		if order_by_columns := self.parsed_query.columns_dict.get("order_by"):
			if self.parsed_query.limit_and_offset:
				possible_indexes.extend(order_by_columns)

		return possible_indexes
