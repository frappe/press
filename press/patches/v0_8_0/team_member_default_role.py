import frappe


def execute():
	TeamMember = frappe.qb.DocType("Team Member")
	frappe.qb.update(TeamMember).set(TeamMember.role, "Developer").where(TeamMember.role.isnull()).run()
	frappe.db.commit()
