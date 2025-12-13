def document_type_key(document_type: str) -> str:
	"""
	Convert a document type to its corresponding key used in permission checks.

	:param document_type: str: The document type (e.g., "Marketplace App").
	:return: str: The corresponding key (e.g., "marketplace_app").
	"""
	return document_type.lower().replace(" ", "_")
