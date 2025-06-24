import frappe
from frappe.query_builder import JoinType
from frappe.query_builder.functions import Count


def execute():
	"""Generate recovery codes for already existing `User 2FA` records."""

	User2FA = frappe.qb.DocType("User 2FA")
	User2FARecoveryCode = frappe.qb.DocType("User 2FA Recovery Code")

	records = (
		frappe.qb.from_(User2FA)
		.join(User2FARecoveryCode, JoinType.left)
		.on(User2FARecoveryCode.parent == User2FA.name)
		.select(User2FA.name)
		.groupby(User2FA.name)
		.having(Count(User2FARecoveryCode.name) == 0)
		.run(as_dict=True)
	)

	for record in records:
		doc = frappe.get_doc("User 2FA", record.name)
		doc.recovery_codes = []
		for code in doc.generate_recovery_codes():
			doc.append("recovery_codes", {"code": code})
		doc.save()
		frappe.db.commit()
