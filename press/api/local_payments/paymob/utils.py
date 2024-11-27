import frappe

@frappe.whitelist(allow_guest=True)
def get_exchange_rate(from_currency, to_currency):
    """Get the latest exchange rate for the given currencies."""
    exchange_rate = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": from_currency, "to_currency": to_currency},
        "exchange_rate",
        order_by="date DESC"
    )
    return exchange_rate or 0.0