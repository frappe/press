"""Check a SQL query that a user without System Manager runs in the System Console.

Raw SQL skips every row filter of Frappe, so the query may only touch DocType
tables that the user can read in full. Anything that the guard does not
understand is refused.
"""

import re

import frappe
import sqlparse
from frappe import _
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.model import table_fields
from frappe.utils.safe_exec import check_safe_sql_query
from sqlparse import tokens as T
from sqlparse.exceptions import SQLParseError

SYSTEM_SCHEMAS = {"information_schema", "mysql", "performance_schema", "sys"}
FIRST_KEYWORDS = {"select", "with", "explain"}
# Statements that write, and functions that wait, lock or change sequences
REFUSED_WORDS = {"insert", "update", "delete", "replace", "drop", "alter", "create", "truncate"}
REFUSED_WORDS |= {"rename", "grant", "revoke", "call", "handler", "set", "do", "load", "lock"}
REFUSED_WORDS |= {"unlock", "into", "outfile", "dumpfile", "load_file", "sleep", "benchmark"}
REFUSED_WORDS |= {"get_lock", "release_lock", "release_all_locks", "is_free_lock", "is_used_lock"}
REFUSED_WORDS |= {"master_pos_wait", "master_gtid_wait", "setval", "nextval", "lastval"}
# Token types that MariaDB reads the same way as sqlparse
PLAIN_TOKEN_TYPES = [T.Whitespace, T.Keyword, T.String.Single, T.String.Symbol, T.Number]
PLAIN_TOKEN_TYPES += [T.Punctuation, T.Operator, T.Wildcard]
PLAIN_NAME = re.compile(r"^(`(?:[^`]|``)*`|[\w$]+)$")


def check_read_only_query(query: str):
	"""Refuse a query that writes, or that reads data the user cannot read."""
	check_safe_sql_query(query)
	if "\\" in query:
		refuse(_("Backslashes are not allowed in the query"))
	if get_user_permissions():
		refuse(_("Raw SQL cannot apply your User Permissions"))
	tokens = list(parse_one_statement(query).flatten())
	check_first_keyword(tokens)
	for token in tokens:
		check_token(token)


def refuse(message: str):
	frappe.throw(message, frappe.PermissionError, title=_("Query refused"))


def parse_one_statement(query: str):
	statements = []
	try:
		statements = [statement for statement in sqlparse.parse(query) if statement.value.strip()]
	except SQLParseError:
		refuse(_("Could not parse the query"))
	if len(statements) != 1:
		refuse(_("Run one statement at a time"))
	return statements[0]


def check_first_keyword(tokens):
	words = [token for token in tokens if not token.is_whitespace]
	if not words or words[0].ttype not in T.Keyword or words[0].normalized.lower() not in FIRST_KEYWORDS:
		refuse(_("Start the query with SELECT, WITH or EXPLAIN"))


def check_token(token):
	# MariaDB and sqlparse read comments and `#` differently, so neither may hide a table
	if token.ttype in T.Comment or (token.ttype not in T.String and "#" in token.value):
		refuse(_("Remove comments from the query"))
	if not is_plain_token(token):
		refuse(_("Could not parse the query near {0}").format(token.value))
	if token.ttype in T.Name or token.ttype in T.Keyword or token.ttype in T.String.Symbol:
		check_identifier(unquote(token.value), is_keyword=token.ttype in T.Keyword)


def is_plain_token(token) -> bool:
	"""sqlparse also knows other dialects, such as `$$` strings that MariaDB reads as names."""
	if token.ttype in T.Name:
		return token.ttype not in T.Name.Placeholder and bool(PLAIN_NAME.match(token.value))
	return any(token.ttype in plain for plain in PLAIN_TOKEN_TYPES)


def unquote(value: str) -> str:
	if len(value) > 1 and value[0] == value[-1] and value[0] in '`"':
		return value[1:-1]
	return value


def check_identifier(name: str, is_keyword: bool):
	lowered = name.lower()
	# sqlparse joins some keywords, such as CREATE OR REPLACE, into one token
	for word in lowered.split():
		if word in REFUSED_WORDS:
			refuse(_("{0} is not allowed in a read-only query").format(word.upper()))
	if lowered in SYSTEM_SCHEMAS or lowered.startswith("__"):
		refuse(_("You cannot read {0}").format(name))
	if lowered.startswith("tab"):
		check_table(name, is_keyword)


def check_table(name: str, is_keyword: bool):
	"""A `tab` name must be the table of a DocType. A SQL keyword such as TABLES is not a table."""
	if doctype := frappe.db.get_value("DocType", {"name": name[3:]}):
		check_doctype(str(doctype))
	elif not is_keyword:
		refuse(_("{0} is not the table of a DocType").format(name))


def check_doctype(doctype: str):
	meta = frappe.get_meta(doctype)
	if meta.istable:
		check_child_table(meta)
		return
	if not can_read_every_record(meta):
		refuse(_("You cannot read every record of {0}").format(doctype))
	check_field_levels(meta)


def can_read_every_record(meta) -> bool:
	"""Raw SQL cannot filter rows, so an `if_owner` rule or a shared record is not enough."""
	roles = set(frappe.get_roles())
	full_read = any(
		perm.read and not perm.permlevel and not perm.if_owner and perm.role in roles
		for perm in meta.permissions
	)
	return full_read and frappe.has_permission(meta.name, "read")


def check_field_levels(meta, parenttype: str | None = None):
	readable = set(meta.get_permlevel_access("read", parenttype))
	if {df.permlevel for df in meta.fields if df.permlevel} - readable:
		refuse(_("{0} has fields that you cannot read").format(meta.name))


def check_child_table(meta):
	parents = get_parent_doctypes(meta.name)
	if not parents:
		refuse(_("{0} is not a table of any DocType that you can read").format(meta.name))
	for parent in sorted(parents):
		if not can_read_every_record(frappe.get_meta(parent)):
			refuse(_("You cannot read {0}, the parent of {1}").format(parent, meta.name))
		check_field_levels(meta, parent)


def get_parent_doctypes(child: str) -> set[str]:
	filters = {"fieldtype": ("in", table_fields), "options": child}
	standard = frappe.get_all("DocField", filters, pluck="parent")
	custom = frappe.get_all("Custom Field", filters, pluck="dt")
	return {*standard, *custom}
