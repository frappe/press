import frappe
from frappe.query_builder.functions import Count, DistinctOptionFunction
from pypika.enums import Order
from pypika.terms import Field

from press.utils import get_current_team


class GroupConcat(DistinctOptionFunction):
	def __init__(self, term: Field, order_by=None, order: Order | str = Order.asc, alias=None):
		super().__init__("GROUP_CONCAT", term, alias=alias)
		self.term = term
		self.order_by = order_by
		self.order = order

	def get_special_params_sql(self, **kwargs):
		order_sql = (
			f" ORDER BY {self.order_by.get_sql(**kwargs)} {self.order.value if isinstance(self.order, Order) else self.order}"
			if self.order_by
			else ""
		)
		return f"{order_sql}"


@frappe.whitelist()
def get_incident_count(resolved: bool = False) -> int:
	team = get_current_team()
	if not team:
		return 0

	site_servers = frappe.get_all(
		"Site",
		{"team": team, "status": ("in", ["Active", "Broken", "Pending"])},
		pluck="server",
	)

	all_user_servers = set(
		site_servers + frappe.get_all("Server", {"team": team}, pluck="name")
	)  # Include shared + dedicated server customers

	if not all_user_servers:
		return 0

	Incident = frappe.qb.DocType("Incident")
	query = (
		frappe.qb.from_(Incident).select(Count(Incident.name)).where(Incident.server.isin(all_user_servers))
	)
	query = (
		query.where((Incident.status == "Resolved") | (Incident.status == "Auto-Resolved"))
		if resolved
		else query.where(Incident.status.isin(["Confirmed", "Validating", "Investigating"]))
	)

	result = query.run(pluck=True)
	return result[0] if result else 0


@frappe.whitelist()
def get_incidents(resolved: bool = False, limit: int = 20, offset: int = 0) -> list[dict]:
	"""Get all active incidents relevant to this team with their investigation details and action steps."""
	team = get_current_team()
	if not team:
		return []

	site_servers = frappe.get_all(
		"Site",
		{"team": team, "status": ("in", ["Active", "Broken", "Pending"])},
		pluck="server",
	)

	all_user_servers = set(
		site_servers + frappe.get_all("Server", {"team": team}, pluck="name")
	)  # Include shared + dedicated server customers

	if not all_user_servers:
		return []

	Incident = frappe.qb.DocType("Incident")
	Investigation = frappe.qb.DocType("Incident Investigator")
	InvestigationAction = frappe.qb.DocType("Action Step")
	query = (
		frappe.qb.from_(Incident)
		.left_join(Investigation)
		.on(Incident.investigation == Investigation.name)
		.left_join(InvestigationAction)
		.on(Investigation.name == InvestigationAction.parent)
		.select(
			Incident.name,
			Incident.server,
			Incident.status,
			Incident.creation,
			Incident.confirmed_at,
			Incident.resolved_at,
			Investigation.name.as_("investigation_name"),
			Investigation.status.as_("investigation_status"),
			Investigation.investigation_findings,
			# comma seperated action steps
			GroupConcat(
				InvestigationAction.step_name,
				order_by=InvestigationAction.idx,
				order=Order.asc,
			).as_("investigation_action_steps"),
			GroupConcat(
				InvestigationAction.status,
				order_by=InvestigationAction.idx,
				order=Order.asc,
			).as_("investigation_action_steps_status"),
		)
		.where(Incident.server.isin(all_user_servers))
	)

	return (
		(
			query.where((Incident.status == "Resolved") | (Incident.status == "Auto-Resolved"))
			if resolved
			else query.where(Incident.status.isin(["Confirmed", "Validating", "Investigating"]))
		)
		.groupby(Incident.name)
		.orderby(Incident.creation, order=Order.desc)
		.limit(limit)
		.offset(offset)
		.run(as_dict=True)
	)
