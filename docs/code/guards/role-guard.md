# Role Guard

## Usage

Role Guard can be used to restrict access to resources based on certain
permissions. It can cover APIs routes, doctypes and specific doctype methods.
Implementation can be found here:
[GitHub](https://github.com/frappe/press/blob/develop/press/guards/role_guard/__init__.py).

[Example](https://github.com/frappe/press/blob/d8d02f37f21b76f49599f7e48647746dd591412c/press/api/billing.py#L506-L516):

```python
@frappe.whitelist()
@role_guard.api("billing")
def get_invoice_usage(invoice):
	team = get_current_team()
	# apply team filter for safety
	doc = frappe.get_doc("Invoice", {"name": invoice, "team": team})
	out = doc.as_dict()
	# a dict with formatted currency values for display
	out.formatted = make_formatted_doc(doc)
	out.invoice_pdf = doc.invoice_pdf or (doc.currency == "USD" and doc.get_pdf())
	return out
```

Here, the `get_invoice_usage` API is protected by the `role_guard` and only
users with the "billing" role can access it. Additionally, we apply a team
filter to ensure that users can only access invoices that belong to their team.

Technically, the `role_guard` checks if the user has the required role in
current team before allowing access to the API. It will not alter your queries
or protect you from writing APIs that can potentially leak data. So, you should
always apply necessary filters to your queries to ensure that users can only
access data they are supposed to.

[Example](https://github.com/frappe/press/blob/d8d02f37f21b76f49599f7e48647746dd591412c/press/api/partner.py#L50-L53):

```python
@frappe.whitelist()
@role_guard.api("partner")
def get_partner_request_status(team):
	return frappe.db.get_value("Partner Approval Request", {"requested_by": team}, "status")
```

Here, the `get_partner_request_status` API is protected by the `role_guard` and
only users with the "partner" role can access it. However, there is no team
filter applied to the query, which means that any user with the "partner" role
can access the status of partner approval requests for any team. This is a
potential security risk as it can lead to data leakage.

## Variants

In addition to the `api` variant, Role Guard also provides `action` and
`document` variants to protect doctype methods and document access
respectively. The usage is similar to the `api` variant, but with some
differences in how you specify the required role and apply necessary filters.

Examples: ([1](https://github.com/frappe/press/blob/d8d02f37f21b76f49599f7e48647746dd591412c/press/press/doctype/server/server.py#L2468-L2471), [2](https://github.com/frappe/press/blob/d8d02f37f21b76f49599f7e48647746dd591412c/press/api/notifications.py#L7-L25))

```python
@role_guard.action()
def validate(self):
	super().validate()
	self.validate_managed_database_service()
```

```python
@frappe.whitelist()
@role_guard.document(document_type=lambda _: "Site")
@role_guard.document(document_type=lambda _: "Release Group")
def get_notifications(
	filters=None,
	order_by="creation desc",
	limit_start=None,
	limit_page_length=None,
	sites=None,
	release_groups=None,
):
```

`role_guard.action` can be used to restrict site and server creations.
`role_guard.document` can be used to restrict access to documents based on the
user's role in the team that the document belongs to. In the above example, we
are restricting access to "Site" and "Release Group" documents.

## Warnings

While Role Guard provides a convenient way to restrict access to resources
based on user roles, it cannot prevent all potential security risks. While a
team check is performed before allowing access to the protected resource, it is
still possible for developers to write APIs that can potentially leak data if
they do not apply necessary filters to their queries. Therefore, it is
important to always apply necessary filters to your queries to ensure that
users can only access data they are supposed to.
