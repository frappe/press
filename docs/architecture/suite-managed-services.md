# Suite Managed Services Follow-Up

## Goal

Turn the manually seeded Suite alpha infrastructure into a regional, capacity-managed service operated by Press without placing Press in the runtime path for meetings or mail access.

This document starts after [Suite managed services alpha](./suite-alpha.md) is live. It records agreed production decisions and deferred work. It is intentionally a separate implementation scope.

## Settled Decisions

- Mail remains one dedicated Stalwart VM per Suite site until safe shared tenancy is proven.
- Mail VMs come from small regional warm pools.
- Meet SFUs are shared and sites have sticky regional placement.
- Mail and Meet normally match the Frappe site's region.
- If regional capacity is unavailable, queue the allocation and add capacity rather than overload or silently cross regions.
- Press owns infrastructure, placement, entitlement, and lifecycle.
- Suite owns the customer-facing experience.
- Press is not called for normal meeting joins or mail access.
- Meet uses per-site Ed25519 keys generated inside Suite and public keys persisted locally on assigned SFUs.
- Meet enforces plan-derived per-site room and participant limits.
- Outbound Mail uses a managed relay rather than fresh tenant VM IPs.
- Mailgun is the initial relay provider.
- Production Mailgun isolation is one subaccount per tenant where supported.
- One custom mail domain is supported per site initially and is globally unique across Suite tenants.
- Custom mail domain setup happens after signup through Suite UI backed by Press APIs.
- The first mailbox attaches to the existing Suite owner.
- Additional mailboxes are assigned explicitly by a Suite administrator.
- External mail clients are a post-alpha capability.
- Suite services are included in Suite plans; service desired state follows Suite entitlement.
- Mail data has a target RPO of one hour and RTO of four hours.
- Mail data is retained for 30 days after cancellation.
- Inbound Mail continues for a seven-day suspension grace period.
- The Mail VM stops after the grace period; an encrypted final backup remains until purge.
- Recovery credentials are available only through audited break-glass access.
- Service upgrades use canary and staged rollout.
- New SFU behavior must remain backward compatible. Deploy service support before dependent Suite code. Use temporary separate pools for genuinely breaking changes rather than building a general capability-negotiation framework initially.

## Infrastructure Automation

### Press Server Types

Replace the alpha inventory-only records with first-class Press server types:

- `Suite Mail Server`, inheriting `BaseServer`
- `Suite Meet Server`, inheriting `BaseServer`

Integrate both types with:

- `Cluster.create_vm`
- provider VM lifecycle
- Press Job and Press Workflow
- Ansible setup and upgrades
- DNS creation and removal
- TLS issue, installation, renewal, and service reload
- monitoring target discovery
- alert routing
- VM snapshots
- archive and decommission workflows

Add explicit types to existing hard-coded VM, server-status, TLS, monitoring, and Press Job registries. Do not introduce a generic infrastructure-service plugin system until another service demonstrates the need.

### Warm Pools

Maintain regional low and high watermarks.

Mail pool states:

```text
Provisioning -> Warm -> Claimed -> Active
                         |          |
                         v          v
                       Broken    Suspended -> Retained -> Purged
```

Meet pool states:

```text
Provisioning -> Active -> Draining -> Archived
                    |
                    v
                  Broken
```

Capacity replenishment is independent of signup. Signup only claims healthy existing capacity.

## Regional Placement

Enable Suite Product Trial clusters only after both service pools have capacity in that region.

Placement rules:

1. Match the site's Cluster region.
2. Select only healthy servers supporting the site's required service behavior.
3. Keep Meet placement sticky.
4. Do not place on draining servers.
5. Keep enough Meet headroom to evacuate the largest server.
6. Queue when no eligible capacity exists.

Meet capacity uses participants, active rooms, bitrate, CPU, and network egress rather than tenant count alone.

## Meet Production Work

### Multiple SFUs

Run multiple independent SFUs per region. Do not initially cluster mediasoup room state across hosts.

Press registers each tenant public key only on its assigned SFU. During planned migration, the key may temporarily exist on the source and destination.

### Draining

For planned maintenance:

1. Mark the source SFU `Draining`.
2. Register tenant keys on the destination.
3. Push the new endpoint to Suite.
4. Send new meetings to the destination.
5. Let existing meetings finish on the source.
6. Remove source registrations after the drain window.

### Failure Reassignment

For unplanned failure:

1. Monitoring declares the assigned SFU unhealthy.
2. Press selects a healthy same-region destination.
3. Press registers tenant keys and pushes the new endpoint.
4. Suite clients detect the terminal disconnect, fetch fresh connection details, reconnect, and republish media.

This is a brief interruption, not seamless media failover. In-memory chat, polls, hands, and participant state may be lost. Preserving live room state requires a separate clustered-SFU design.

### Key Lifecycle

- Rotate per-site signing keys without moving the tenant.
- Keep old and new public keys during a bounded overlap.
- Revoke keys immediately on tenant deletion or security incident.
- Disable the tenant registry entry on suspension.
- Audit registry changes in Press and on the SFU.

## Mail Production Work

### Multi-Region Warm Pools

Start with AWS, where Press already supports Elastic IP allocation. Add providers only after validating static IP, PTR, snapshot, and restore capabilities.

Use one standard Mail VM shape initially. Introduce plan-based resizing only after real usage data exists.

Every Mail VM requires:

- static public IP
- provider-managed PTR/rDNS
- stable service hostname
- encrypted data volume
- application-consistent checkpoint and snapshot jobs
- JMAP, SMTP inbound, queue, disk, and certificate monitoring
- tested restore metadata

### Automatic Recovery

On VM failure:

1. Provision a replacement in the same region.
2. Reattach the encrypted data volume and static IP where healthy.
3. Restore the latest application-consistent snapshot only if the volume is unavailable.
4. Restore service credentials from secret references.
5. Verify JMAP, inbound SMTP, outbound relay, and push callbacks.
6. Return the allocation to `Ready`.

Target RPO is one hour. Target RTO is four hours. Run scheduled restore drills rather than treating snapshot success as proof of recoverability.

### Custom Domain Control Plane

Suite presents the UI, while authenticated Press APIs own:

- global domain reservation
- ownership challenge generation
- DNS verification
- Stalwart domain creation
- Mailgun subaccount and sender-domain setup
- expected MX, SPF, DKIM, DMARC, and client-discovery records
- activation status
- suspension and deletion

One complete domain belongs to one immutable Suite tenant. A domain cannot be attached to another site without an explicit transfer workflow.

Press automatically writes records only for DNS zones it owns. External DNS users receive copyable records and periodic verification.

Domain replacement is support-assisted initially:

1. Verify and reserve the new domain.
2. Configure Stalwart and Mailgun.
3. Migrate addresses or create bounded aliases.
4. Switch DNS and verify delivery.
5. Retain a rollback window.
6. Retire and release the old domain.

### Mailgun Isolation And Abuse

Create one Mailgun subaccount per Suite tenant where the provider plan permits it. Give each tenant distinct SMTP credentials, quotas, webhook attribution, suppression state, and suspension controls.

Enforce per-tenant and per-mailbox send limits. Consume delivery, bounce, spam complaint, and suppression events. Automatically freeze outbound delivery when thresholds are exceeded while preserving inbound delivery and administrative recovery.

Do not rely on account-wide Mailgun suspension as the first tenant isolation boundary.

### Mailbox Lifecycle

- Attach the owner's first mailbox to the existing Frappe user.
- Let Suite administrators explicitly assign additional mailbox seats and addresses.
- Make account and app-password creation transactional or compensating.
- Reconcile orphaned Stalwart accounts and Suite mappings.
- Support credential rotation without changing the Frappe login identity.
- Add supported external-client app-password generation when IMAP and SMTP submission are launched.

### Suspension And Retention

At suspension:

1. Disable authentication and outbound delivery immediately.
2. Continue inbound delivery for seven days.
3. Reject new inbound SMTP after the grace period.
4. Create and verify a final backup.
5. Terminate compute and release warm capacity after day seven.
6. Retain encrypted data until day 30.
7. Purge data, credentials, DNS, Mailgun resources, static IP, and allocation metadata after retention.

Resumption before purge restores the allocation, rotates credentials where appropriate, verifies service health, and re-enables traffic.

## Billing And Entitlements

Keep Suite billing visible inside Suite and implemented by Press.

Production work includes:

- full payment-method management inside Suite
- plan changes and displayed service limits
- idempotent trial conversion
- payment failure and retry status projection
- plan-derived Mail storage/seats and Meet capacity
- add-ons only if product requirements later call for extra storage, seats, or meeting capacity

Service allocations follow the Suite site's entitlement rather than separate customer-visible Mail and Meet subscriptions.

## Reconciliation

Run a scheduled reconciler over deployments and allocations.

Every operation is at least once and keyed by:

```text
tenant_id + service + desired_generation
```

The reconciler must:

- repair interrupted provisioning
- detect stale jobs
- prevent old retries from overwriting newer suspension or deletion
- detect orphaned provider resources
- detect missing SFU registrations
- verify Mail endpoint ownership and credentials
- retry transient failures with bounded backoff
- expose terminal failures to operators
- never destroy mailbox data as generic compensation

## Secrets

Press currently persists Ansible variables and Agent Job request data. Before full infrastructure automation:

- store secrets in encrypted fields or a dedicated secret store
- pass secret references through jobs
- resolve secrets immediately before execution
- redact workflow output and provider errors
- separate Press recovery credentials from Suite tenant credentials
- rotate registry, relay, and tenant credentials independently
- audit every break-glass reveal and privileged operation

## Monitoring And SLOs

### Meet

- endpoint and signaling health
- mediasoup worker health
- CPU, memory, packet loss, bitrate, and network egress
- active rooms and participants by tenant
- tenant limit rejection counts
- reconnect and authentication failure rates
- capacity headroom and drain progress

### Mail

- JMAP and SMTP endpoint health
- inbound and outbound queue age
- delivery, bounce, and complaint rates
- disk and data-volume health
- snapshot age and restore-test age
- certificate validity
- Mailgun credential and domain status
- spam and abuse freezes

### Control Plane

- signup-to-Meet-ready latency
- card-to-Mail-ready latency
- queued allocation age
- pool watermarks
- failed reconciliation count
- stale Suite status projections

## Upgrade Policy

Use canary and staged service rollout.

Rules:

1. Service changes must preserve behavior used by the current and immediately previous Suite release.
2. Deploy backward-compatible service support before the Suite release that needs it.
3. Canary on internal tenants, then a small production cohort, then regional batches.
4. Pause automatically on health or customer-journey regression.
5. Use temporary version-specific server pools for genuinely breaking changes.
6. Remove old behavior only after old Suite releases are gone.

Do not build a general runtime capability-negotiation framework until a concrete feature requires it.

## Shared Mail Evaluation

Shared Stalwart is not part of the committed architecture. Evaluate it only if dedicated VM economics require it and Stalwart can enforce:

- tenant-scoped administration
- domain and account ownership
- runtime data isolation
- quotas and abuse isolation
- tenant-aware backup, restore, export, and deletion
- credentials that cannot enumerate or mutate another tenant

Until those properties pass adversarial tests, retain dedicated Stalwart VMs.

## Delivery Order

1. Automate AWS Mail and Meet server creation.
2. Add regional warm-pool replenishment and capacity alerts.
3. Add SFU draining and failure reassignment.
4. Add automatic Mail rebuild and tested restore.
5. Add custom-domain control plane.
6. Move Mailgun tenants to subaccounts.
7. Automate suspension, retention, purge, and resumption.
8. Add supported external mail clients.
9. Add further regions and providers.
10. Reassess shared Mail only after operational cost data exists.
