import frappe


def execute():
    # might not be needed if the key is added manually from https://frappecloud.com/app/site-config-key
    # and subsequently distributed from 
    if not frappe.db.exists("Site Config Key", {"key": "max_storage_usage"}):
        frappe.get_doc(
            doctype="Site Config Key", 
            internal=True, 
            key="max_storage_usage",
            type="number"
            ).insert(ignore_permissions=True)
    # Maybe this should also update all non archived sites? Not sure
    non_archived_sites = frappe.get_all(
        "Site", filters={"status": ("!=", "Archived")}, pluck="name"
    )

    for site in non_archived_sites:
        site_doc = frappe.get_cached_doc("Site", site)
        plan = frappe.db.get_value("Site Plan", site_doc.plan)
        site._update_configuration({"max_storage_usage": plan.max_storage_usage})