import frappe
from frappe.utils import cint

from press.utils import get_current_team


def rebuild_search_index_for_doctype(doctype):
	if doctype == "Site":
		filters = {"status": ("!=", "Archived")}
		fields = ["name", "team"]
	elif doctype == "Release Group":
		filters = {"enabled": 1}
		fields = ["name", "title", "team"]
	elif doctype == "Server":
		filters = {"status": "Active"}
		fields = ["name", "title", "team"]

	records = frappe.get_all(doctype, fields=fields, filters=filters)

	frappe.db.delete("__press_search", {"doctype": doctype})

	for record in records:
		record.doctype = doctype
		add_index_for_document(record)


def rebuild_search_index():
	doctypes_to_index = ["Site", "Release Group", "Server"]

	for doctype in doctypes_to_index:
		frappe.enqueue(rebuild_search_index_for_doctype, doctype=doctype)


def delete_index_for_document(doc):
	frappe.db.delete("__press_search", {"doctype": doc.doctype, "name": doc.name})


def add_index_for_document(doc):
	press_search = frappe.qb.Table("__press_search")

	route = get_route(doc)
	title = get_title(doc)

	frappe.qb.into(press_search).insert(
		doc.doctype, title, route, doc.team, doc.name
	).run()


def update_index_for_document(doc):
	delete_index_for_document(doc)

	if (doc.doctype in ("Site", "Server") and doc.status == "Archived") or (
		doc.doctype == "Release Group" and not cint(doc.enabled)
	):
		return

	add_index_for_document(doc)


def get_route(doc):
	if doc.doctype == "Release Group":
		return f"/benches/{doc.name}/overview"
	elif doc.doctype == "Site":
		return f"/sites/{doc.name}/overview"
	elif doc.doctype == "Server":
		return f"/servers/{doc.name}/overview"


def get_title(doc):
	try:
		title = doc.title or doc.name
	except AttributeError:
		title = doc.name

	return title


@frappe.whitelist()
def search(text, start=0, limit=20):
	from frappe.query_builder.functions import Match

	team = get_current_team()

	press_search = frappe.qb.Table("__press_search")
	rank = Match(press_search.title).Against(text).as_("rank")

	query = (
		frappe.qb.from_(press_search)
		.select(press_search.title, press_search.route, press_search.doctype, rank)
		.where(press_search.team == team)
		.orderby("rank", order=frappe.qb.desc)
		.limit(limit)
	)

	if cint(start) > 0:
		query = query.offset(start)

	results = query.run(as_dict=True)

	return [result for result in results if result.rank > 0]
