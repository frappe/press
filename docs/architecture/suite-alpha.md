# Suite Managed Services Alpha

## Status

- Target: production alpha
- Entry point: Frappe Cloud Product Trial signup for Suite
- Access: open signup
- Expected load: low
- Region: one Suite-enabled AWS region

## Goal

Deliver this customer journey end to end:

1. A user starts from the Suite website and opens the visible Frappe Cloud Product Trial signup.
2. The user chooses the normal Frappe site subdomain and creates a Suite trial site.
3. Press claims a Suite standby site and assigns it to the user.
4. Press allocates the site to the shared Meet SFU.
5. The user enters Suite and can use the other Suite apps and Meet without adding a card.
6. Suite presents an embedded Stripe payment form when the user chooses to unlock Mail.
7. Adding a valid payment method preserves the remaining trial and starts Mail provisioning.
8. Press claims a pre-provisioned dedicated Mail VM, creates a managed starter mail domain and first mailbox, and pushes sanitized status into Suite.
9. The owner can send and receive mail through Suite's web Mail UI.
10. At trial expiry, Press automatically converts a card-backed Suite trial to the Product Trial's configured paid plan.

After the initial redirect into the site, customers must not need the Frappe Cloud dashboard. Billing, service status, and Mail activation are presented inside Suite.

## Non-Goals

- Creating Mail or Meet VMs automatically.
- Automatically replenishing warm capacity.
- Multiple regions or cloud providers.
- Customer custom mail domains.
- More than one mail domain per site.
- Supported IMAP, SMTP submission, or mobile-client setup.
- Mailgun subaccounts per tenant.
- Automatic Mail VM rebuild.
- Automatic SFU failover or client reconnection.
- Horizontal SFU clustering.
- Self-service mail-domain migration.
- Shared Stalwart instances across tenants.
- Automatic Mail disk expansion or quota enforcement.
- Exposing Press jobs, servers, errors, or retry controls to Suite users.
- General Suite installation on existing sites. Suite is available only through its Product Trial signup.

The deferred production design is in [Suite managed services follow-up](./suite-managed-services.md).

## Architecture

```text
Suite website
    -> Frappe Cloud Product Trial signup
    -> Suite standby site claimed
    -> Suite Deployment created in Press
       -> Meet Allocation -> one shared, pre-provisioned SFU
       -> Mail Allocation -> locked until valid card
                           -> one dedicated, pre-provisioned Stalwart VM
    -> sanitized state pushed into Suite
```

Press is authoritative for entitlement, allocation, billing, and infrastructure state. Suite stores only the customer-facing status and credentials required to use its assigned services.

Press is not in the runtime path for meetings or normal mail access.

## Alpha Capacity

Operators provision the following before enabling signup:

- One shared Meet SFU in the Suite AWS region.
- A small fixed pool of sanitized, dedicated Mail VMs in the same region.
- Stable DNS and TLS for every service endpoint.
- One encrypted Mail data volume per VM.
- Hourly Mail data snapshots.
- Monitoring and alerts for endpoint health, disk usage, and pool exhaustion.

Press automates allocation and tenant configuration only. If capacity is exhausted, allocations remain queued, Suite shows that setup is in progress, and operators add capacity manually.

## Press Model

### Suite Deployment

One record per claimed Suite site.

Required fields:

- `site`
- `team`
- `product_trial_request`
- `tenant_id`: immutable generated identifier
- `region`
- `desired_state`: `Active`, `Suspended`, `Deleted`
- `status`: aggregate customer-facing readiness
- `generation`: incremented for each desired-state change

`site` is unique. A site hostname change does not change `tenant_id`.

### Suite Service Allocation

One record per deployment and service.

Required fields:

- `suite_deployment`
- `service`: `Mail` or `Meet`
- `server`
- `desired_state`
- `status`
- `generation`
- `endpoint`
- `external_id`
- `last_error`
- `last_reconciled_at`

The pair `(suite_deployment, service)` is unique.

Allocation statuses:

```text
Locked
Pending
Queued
Provisioning
Configuring
Ready
Suspended
Failed
Deleting
Deleted
```

### Suite Meet Server

Inventory for manually provisioned SFUs.

Required fields:

- `endpoint`
- `region`
- `status`: `Active`, `Draining`, `Broken`
- `registry_admin_secret`
- `max_participants`
- `active_participants`
- `active_rooms`
- `assigned_tenants`

### Suite Mail Server

Inventory for manually provisioned dedicated Stalwart VMs.

Required fields:

- `hostname`
- `endpoint`
- `region`
- `status`: `Warm`, `Claimed`, `Active`, `Suspended`, `Broken`
- `allocated_site`
- `recovery_credential`
- `data_volume_id`
- `static_ip`
- `last_snapshot`

Only `Warm` servers may be claimed. Claiming must lock the row and be idempotent.

## Provisioning Trigger

`Product Trial Request` is the sole Suite entitlement entry point.

When a Suite standby site is claimed and linked to a real team, Press calls an idempotent `ensure_suite_deployment(site)` after commit. Standby sites must not receive Mail or Meet allocations.

`ensure_suite_deployment` performs these actions:

1. Verify that the site belongs to the Suite Product Trial.
2. Create or load the unique `Suite Deployment`.
3. Create or load the Meet allocation and enqueue Meet configuration.
4. Create the Mail allocation in `Locked` state unless the team already has a valid default payment method.
5. Push the initial sanitized status to Suite once the site is reachable.

Do not add Mail or Meet jobs to `Product Trial Request.tracked_agent_jobs`. Site creation and external service readiness remain independent state machines, and service failure must not roll back a working Frappe site.

## Meet Alpha

### Tenancy

All alpha Suite sites share one regional SFU. Each site remains pinned to that SFU for the alpha.

The SFU enforces these per-tenant limits:

- 50 active participants
- 5 concurrent rooms

Room identity uses the immutable `tenant_id`, not a client-provided site hostname.

### Authentication

The current global HS256 `sfu_secret` is not acceptable for open signup.

Required Suite changes:

1. Generate an Ed25519 key pair inside each Suite site.
2. Store the private key encrypted in the site database.
3. Return only the public key and `key_id` to Press through an authenticated provisioning call.
4. Sign meeting tokens locally with EdDSA.
5. Include `tenant_id`, `kid`, `iss`, `aud`, meeting, user, permissions, `iat`, and `exp` claims.

Required SFU changes:

1. Add a Press-authenticated tenant registry API.
2. Persist tenant IDs, public keys, enabled state, and limits on a mounted local volume.
3. Verify tokens using the registered public key selected by `tenant_id` and `kid`.
4. Reject unknown, disabled, expired, wrongly scoped, or over-limit tenants.
5. Derive the room namespace from the verified tenant identity.

The alpha may use an atomically written local registry file because there is one SFU process and low write volume. Press is used only to register lifecycle changes; meeting creation and joining continue if Press is unavailable.

### Meet Allocation Sequence

1. Create the pending Meet allocation.
2. Select the healthy active SFU in the Suite region.
3. Ask the Suite site to ensure its key pair and return the public key.
4. Register the tenant, public key, and limits on the SFU using an idempotency key.
5. Push the SFU endpoint and tenant identity to Suite.
6. Request connection details from Suite and verify a real token against the SFU.
7. Mark the allocation `Ready` and push status.

Failure is retried automatically. Suite exposes no retry button. Automatic reassignment to another SFU is deferred.

## Mail Alpha

### Isolation

Each card-verified Suite site receives one dedicated Stalwart VM. Stalwart is not shared between tenants.

Press keeps a recovery administrator credential. Suite receives a separate rotatable tenant administrator credential for its dedicated server. Recovery access is not routinely exposed and is reserved for audited break-glass use.

### Mail Entitlement

Meet and the other Suite apps are available during the trial without a card. Mail starts in `Locked` state.

Mail becomes entitled when the Team has a valid default payment method. Adding the card does not end the trial.

If the only valid payment method is removed:

1. Set Mail desired state to `Suspended`.
2. Disable mailbox login and outbound delivery.
3. Continue accepting inbound mail for a seven-day grace period.
4. Preserve mailbox data for 30 days.

For the alpha, resource shutdown and final purge may use an operator runbook. Their automation belongs to the follow-up spec.

### Managed Starter Domain

The alpha does not accept a customer custom mail domain. Press creates one domain beneath a configurable Frappe-owned mail root:

```text
<site-subdomain>.<managed-mail-root>
```

The first mailbox reuses the signup email's local part:

```text
alice@gmail.com -> alice@<site-subdomain>.<managed-mail-root>
```

The mailbox is attached to the existing Suite owner through `User Account`. Do not create a second Frappe user for the mailbox.

Additional Suite users do not receive mailboxes automatically. Admin-assigned mailboxes are deferred unless already trivial in the existing Mail UI.

### Outbound Delivery

Stalwart relays outbound mail through Mailgun.

For the alpha:

- Use one Frappe-owned Mailgun account.
- Create a distinct managed sender domain and SMTP credential per Suite tenant.
- Attribute webhook and abuse events to the tenant domain.
- Freeze outbound delivery automatically on abuse thresholds.
- Do not use one SMTP credential across all Mail VMs.

Mailgun subaccounts per tenant are deferred.

### Mail Allocation Sequence

1. A successful embedded Stripe setup marks the locked Mail allocation eligible.
2. Atomically claim one `Warm` Mail server in the Suite region.
3. Rotate or create the tenant administrator credential.
4. Create the managed starter domain in Stalwart.
5. Create the Mailgun sender domain and per-domain SMTP credential.
6. Configure Stalwart's outbound next hop.
7. Configure Suite `Mail Settings` with the endpoint and encrypted tenant credential.
8. Require encrypted JMAP push notifications.
9. Create the owner's mailbox and attach it to the existing Frappe user.
10. Verify JMAP access and an outbound/inbound test path.
11. Mark the allocation `Ready` and push status to Suite.

Provider calls and account creation are at-least-once operations. Use deterministic resource names and the key `tenant_id + service + generation` for idempotency. Never delete mailbox data as generic rollback.

### Mail Access

Only Suite's web Mail UI is supported in the alpha. Third-party IMAP, SMTP submission, autoconfiguration, and mobile-client support are not part of acceptance.

The alpha does not expose a marketed mailbox quota or automated disk enforcement. Disk monitoring and operator alerts are still required; the lack of enforcement is an explicitly accepted alpha risk.

## Billing Inside Suite

Suite renders an embedded Stripe payment element. The browser never receives Press credentials.

New site-authenticated SaaS APIs in Press should reuse `fc_communication_secret` and must verify that the caller belongs to an active Suite Product Trial:

- Fetch sanitized billing context and the configured paid conversion plan.
- Create or reuse a Stripe SetupIntent for the Team customer.
- Confirm setup and create the Team payment method using the existing Press billing helpers.
- Return only the Stripe client data and sanitized result needed by Suite.

Adding a card triggers Mail entitlement but preserves `trial_end_date`.

Add a paid conversion plan to the Suite Product Trial configuration. At trial expiry, an idempotent scheduled process must:

1. Lock the site and confirm it is still on the Suite trial plan.
2. Confirm the Team has a valid payment method.
3. Change the site to the Product Trial's configured conversion plan.
4. Clear `trial_end_date` through the normal plan-change path.
5. Leave sites without a valid payment method on the normal expired-trial suspension path.

The price and conversion consent must be shown when the card is added.

## Status Projection

Press stores detailed infrastructure state and errors. Suite stores a sanitized local projection.

Add a narrow Suite endpoint authenticated with the existing Frappe Cloud communication secret. Press pushes updates containing:

- service
- public status
- short user-safe message
- generation
- timestamp

Suite rejects stale generations and never stores Press tracebacks or provider payloads.

Suggested customer states:

```text
Meet: Setting up | Ready | Temporarily unavailable
Mail: Add payment method | Queued | Setting up | Ready | Suspended | Temporarily unavailable
```

Suite retries nothing directly. Press reconciles automatically, while operators retain detailed retry controls in Press.

## Security Requirements

- Never send Meet private keys to Press or the SFU.
- Never share the current global SFU secret across Suite tenants.
- Store Mail and SFU administration credentials in encrypted fields.
- Pass secret references to jobs where possible; do not copy secrets into workflow output or request logs.
- Verify Suite entitlement on every hidden SaaS API.
- Authenticate Press-to-Suite status updates and reject replayed generations.
- Authenticate the SFU tenant registry API separately from tenant meeting tokens.
- Require encrypted JMAP push payloads.
- Keep Press recovery access separate from Suite's tenant Mail credential.

## Failure Behavior

- Site creation succeeds independently of Mail or Meet provisioning.
- Meet or Mail failure does not archive or roll back the Suite site.
- Failed allocations are retried with bounded backoff.
- Pool exhaustion produces `Queued`, not `Failed`.
- Adding a card succeeds even if the Mail pool is empty.
- Operator alerts fire for terminal failure, pool exhaustion, unhealthy endpoints, snapshot failure, and high disk usage.
- Automatic Mail rebuild and SFU reassignment are deferred; alpha recovery uses monitored operator runbooks.

## Implementation Split

### Press

- Suite deployment, allocation, and pre-provisioned server inventory DocTypes.
- Product Trial-only provisioning trigger.
- Meet and Mail allocation workflows.
- Hidden Suite billing APIs and trial-expiry conversion.
- Mailgun domain/credential provisioning.
- SFU registry client.
- Sanitized status push.
- Reconciliation, alerts, and operator retry controls.

### Suite Backend

- Local service-status model and authenticated status endpoint.
- Embedded billing backend calls to Press.
- Meet tenant identity and Ed25519 key generation/signing.
- Mail configuration endpoint that stores credentials encrypted.
- First mailbox creation attached to the existing owner.
- Enforcement that managed cloud infrastructure is not configured through customer-facing server deployment DocTypes.

### Suite Frontend

- Mail locked/setup/ready/suspended experience.
- Embedded Stripe payment element and conversion consent.
- Sanitized service status.
- No Frappe Cloud links after the initial site redirect.

### Meet SFU

- Persistent local tenant public-key registry.
- Registry administration API.
- EdDSA token verification and immutable tenant room namespace.
- Per-tenant room and participant limits.

### Operations

- Provision and validate the first SFU.
- Provision and sanitize the fixed Mail VM pool.
- Configure DNS, TLS, firewall, encrypted volumes, hourly snapshots, and monitoring.
- Document capacity-addition, Mail restore, SFU recovery, suspension, and purge runbooks.

## Acceptance Criteria

1. A new Suite Product Trial claims a standby site without allocating services to unclaimed standby sites.
2. The user lands in Suite even while service allocation is incomplete.
3. Meet becomes ready without a payment method.
4. Tokens from one Suite tenant cannot authenticate as another tenant.
5. A tenant cannot exceed 50 participants or 5 concurrent rooms.
6. Mail remains locked until a valid payment method is added inside Suite.
7. Adding a card does not clear the trial end date.
8. Adding a card with an empty Mail pool succeeds and leaves Mail queued.
9. With capacity, one warm Mail VM is claimed exactly once.
10. The managed starter domain and first mailbox are created without creating another Frappe user.
11. The owner sends and receives a message through Suite's web Mail UI.
12. Outbound mail uses tenant-specific Mailgun domain credentials.
13. Suite displays only sanitized service state and no Frappe Cloud UI after login.
14. At trial expiry, a card-backed site changes to the configured paid plan exactly once.
15. An expired site without a valid payment method follows the normal suspension path.
16. Removing the only payment method suspends Mail entitlement without immediately deleting mailbox data.
17. Re-running any provisioning step does not create duplicate tenants, domains, mailboxes, or allocations.

## Launch Configuration

These values must be filled before enabling the alpha:

- Suite Product Trial name
- Suite trial Site Plan
- Suite paid conversion Site Plan and displayed price
- Trial duration
- AWS region and Cluster
- Meet hostname, instance shape, and total safe capacity
- Managed mail root domain
- Standard Mail VM shape and encrypted data volume size
- Number of warm Mail VMs
- Mailgun account, webhook secret, and API permissions
- Snapshot retention
- Customer-facing support contact and timeout copy

## Accepted Alpha Risks

- Fixed manually replenished capacity can queue new users.
- One SFU is a regional single point of failure.
- Mail recovery and SFU reassignment require operators.
- Mail has monitoring but no automated quota or disk enforcement.
- Mailgun account isolation is by tenant domain credential, not subaccount.
- Only the managed starter domain and web Mail UI are supported.
- Infrastructure lifecycle automation is intentionally incomplete.
