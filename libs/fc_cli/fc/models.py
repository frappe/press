from typing import TypedDict


class ClientList(TypedDict):
	doctype: str
	filters: dict[str, str]
	fields: list[str]
	start: int
	limit: int
	limit_start: int
	limit_page_length: int
	debug: bool | int


class ClientGet(TypedDict):
	doctype: str
	name: str


class ClientRunDocMethod(TypedDict):
	dt: str
	dn: str
	method: str
