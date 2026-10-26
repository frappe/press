import sqlparse
from sqlparse.exceptions import SQLParseError


def format_sql(query: str, strip_comments: bool = False) -> str:
	"""Pretty-print a query, or return it unchanged if it is too large for sqlparse"""
	query = query.strip()
	try:
		formatted = sqlparse.format(query, keyword_case="upper", reindent=True, strip_comments=strip_comments)
	except SQLParseError:
		return query
	return formatted.strip()
