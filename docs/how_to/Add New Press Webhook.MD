---
route: add-new-press-webhook
allow_guest: 1
published: 1
---

General introduction to press webhook can be found in [the public documentation](https://frappecloud.com/docs/webhook-introduction).

Add New Webhook Event
---------------------

1. Go to `Press Webhook Event` doctype in desk.
2. Create a new record and fill up the title and description of event. This title and description will be shown to users to select.
3. If you are on local development setup, you can export fixtures.
4. Update the documentation of `Webhook Events` as well > <https://frappecloud.com/docs/webhook-events>

Create Webhook Event
--------------------

1. Import the method


```
from press.utils.webhook import create_webhook_event
```
2. Call the method with webhook event name, payload and team name


```
create_webhook_event("Site Status Update", payload, team_name)
```

	* **Payload** can be doctype object or a python dictionary.
	* If you want to pass doctype object as payload, you should add the required non-sensitive fields in `dashboard_fields` list in your doctype class. Check the `_process_document_payload` method ([ref](https://github.com/frappe/press/blob/d548d10269fb31dacc5ce257a8ff2d41fe451d6a/press/utils/webhook.py#L66)) to understand that.
3. ⚠️ In the codebase, at many place we use `frappe.db.set_value` to set some specific field's value, it can cause little bit issues.

  


Assume a case, you want to create a webhook event whenever the site status got updated. Simplest way is to call the `create_webhook_event` function inside `on_update` hook.

  


It may not work because in agent job update process functions and other places, we use `set_value` call. So, we need to call this `create_webhook_event` function at those places as well.

Related Doctypes
----------------

1. **Press Webhook Event** - Type of webhook events (e.g. *Site Status Update*).
2. **Press Webhook** - Holds the configured webhook of teams.
3. **Press Webhook Selected Event** - Child table to hold selected events for `Press Webhook` doctype.
4. **Press Webhook Log** - This doctype record gets created, when we try to dispatch a webhook event to a team. It has a child table `Press Webhook Attempts` which hold request/response of webhook calls. Also manage status, retry information as well.
5. **Press Webhook Attempt** - Child table which hold request, response, status code, overall status, timestamp of a webhook request.
