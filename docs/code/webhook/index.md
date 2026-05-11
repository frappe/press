# Webhooks

Webhooks allow teams to receive HTTP callbacks when specific events occur in
Press — site status changes, plan upgrades, bench deployments, and more. The
public-facing documentation lives at
[frappecloud.com/docs/webhook-introduction](https://frappecloud.com/docs/webhook-introduction).

## How It Works

1. A team configures a **Press Webhook** with an endpoint URL, a secret, and
   one or more selected events.
2. When something noteworthy happens (e.g. a site changes status), the
   codebase calls `create_webhook_event`.
3. If any enabled webhook for that team is subscribed to the event, a **Press
   Webhook Log** is created with status `Pending`.
4. A scheduled job (`process`) picks up pending logs and enqueues them for
   delivery.
5. Each delivery attempt is recorded as a **Press Webhook Attempt** child row
   on the log.
6. On failure, the log is retried with exponential back-off (2^n minutes, up
   to 3 retries).
7. Webhooks with a >70% failure rate over the past hour are automatically
   disabled and the team owner is notified by email.
8. Logs older than 24 hours are cleaned up automatically.

## Doctypes

| Doctype | Purpose |
|---------|---------|
| **Press Webhook Event** | Defines the types of events available for subscription (e.g. *Site Status Update*). Has a title, description, and enabled flag. |
| **Press Webhook** | Stores a team's configured webhook — endpoint URL, secret, enabled flag, and selected events. Limited to 5 per team. |
| **Press Webhook Selected Event** | Child table of `Press Webhook` holding the events a webhook is subscribed to. |
| **Press Webhook Log** | Created when an event fires. Tracks status (`Pending`, `Queued`, `Sent`, `Partially Sent`, `Failed`), retry count, and the serialised request payload. |
| **Press Webhook Attempt** | Child table of `Press Webhook Log`. Records each HTTP call — endpoint, response body, status code, overall status, and timestamp. |

## Firing a Webhook Event

Import the helper and call it with the event name, payload, and team:

```python
from press.utils.webhook import create_webhook_event

create_webhook_event("Site Status Update", payload, team_name)
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `str` | The event name — must match a `Press Webhook Event` record. |
| `payload` | `dict \| Document` | The data to send. Can be a plain dictionary or a Frappe `Document`. |
| `team` | `str` | The team name to look up configured webhooks for. |

The function returns `True` on success and `False` if an exception occurs
(errors are logged via `frappe.log_error`).

### Payload Handling

- **Dictionary payloads** are sent as-is.
- **Document payloads** are filtered through `_process_document_payload`,
  which only includes Frappe's default fields plus any fields listed in the
  document class's `dashboard_fields` attribute. This prevents leaking
  sensitive data. Fields in `UNNECESSARY_FIELDS_OF_PAYLOAD` (`build_steps`,
  `apps`) are always excluded.

To expose fields for a doctype's webhook payload, add them to
`dashboard_fields` on the class:

```python
class SitePlanChange(Document):
    dashboard_fields = ("from_plan", "to_plan", "type", "site", "timestamp")
```

### Usage Examples

**Document payload** — the `Site` document is filtered automatically:

```python
def create_site_status_update_webhook_event(site: str):
    record = frappe.get_doc("Site", site)
    if record.team == "Administrator":
        return
    create_webhook_event("Site Status Update", record, record.team)
```

**Inside a hook** — `SitePlanChange` fires an event after insert:

```python
def after_insert(self):
    if self.team != "Administrator":
        create_webhook_event("Site Plan Change", self, self.team)
```

**Inside a job update callback** — status set via `set_value`:

```python
frappe.db.set_value("Bench", job.bench, "status", updated_status)
if bench.team != "Administrator":
    bench.status = updated_status
    create_webhook_event("Bench Status Update", bench, bench.team)
```

::: warning
`frappe.db.set_value` bypasses document hooks like `on_update`. If the event
is fired only inside `on_update`, code paths that use `set_value` (e.g. Agent
Job update callbacks) will silently skip it. Always call `create_webhook_event`
explicitly at those points as well.
:::

## Adding a New Webhook Event

1. Open the **Press Webhook Event** doctype in Desk.
2. Create a new record with a descriptive title and description — these are
   shown to users when selecting events.
3. On a local development setup, export fixtures so the new event is included
   in the repository.
4. Call `create_webhook_event` at every code path where the event should fire
   (hooks *and* `set_value` paths).
5. Update the public
   [Webhook Events](https://frappecloud.com/docs/webhook-events)
   documentation.
