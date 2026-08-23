# Minit — Strategic Next Steps

Minit's product direction is intentionally simple:

> **Deploy software to your own computer. Manage it like the cloud.**

The local machine remains the application runtime and source of truth. Minit should earn the right to add cloud services only after the local experience is dependable.

This document describes the strategic sequence rather than the detailed engineering checklist. The detailed implementation roadmap remains in GitHub Issue #7.

## Step 1 — Make the local runtime boringly reliable

**Goal:** a non-expert should be able to turn an AI-built app into a dependable local service with one command.

Core experience:

```text
build app
  ↓
minit deploy
  ↓
close terminal
  ↓
app keeps running
  ↓
crash / login / reboot
  ↓
Minit brings it back
```

Already validated on hosted Windows/macOS/Linux environments:

- one-command deploy for common web apps
- detached local lifetime
- multiple apps with collision-safe ports
- targeted stop/restart from another directory
- crash and forced-child-kill recovery
- Windows Credential Manager persistence
- Windows Task Scheduler register/run/remove
- cross-platform unit/package CI

Remaining gate before considering the local runtime mature enough for an alpha audience:

- physical Windows/macOS/Linux login/reboot validation
- sleep/wake behavior
- 72-hour multi-app dogfood on real desktops
- clean upgrade/uninstall behavior

**Release gate:** consider `0.2.0a1` after real-device persistence succeeds. Do not call the local runtime production-ready merely because hosted CI passes.

## Step 2 — Protect the user's computer from the app

**Goal:** an AI-generated app should not automatically inherit the authority of the human user account running Minit.

This is the largest remaining security gap.

Target boundary:

```text
Minit manager / gateway
        │
        │ controlled interface
        ▼
┌─────────────────────────────┐
│ sandboxed app               │
│ project code: read-only     │
│ .minit/data: read/write     │
│ scoped temp                 │
│ declared secrets only       │
│ explicit network policy     │
└─────────────────────────────┘

NOT automatically accessible:
~/Documents
~/.ssh
other Minit apps
unrelated credentials/keyring
```

Work includes:

- practical sandbox implementations per OS rather than pretending the three platforms are identical
- Windows ACL hardening for Minit state
- filesystem and network permissions
- stronger separation between app process and Minit key material
- malicious same-user app tests

**Gate:** Minit should be able to explain precisely what a managed app can and cannot read/write/connect to.

## Step 3 — Make sharing private, persistent, and locally authorized

**Goal:** move beyond temporary Quick Tunnels without turning Minit's server into a privileged backdoor.

Current `minit run` is useful for demos, but the permanent architecture should be:

```text
authorized browser/client
        │
        │ end-to-end protected session
        ▼
blind relay/router when needed
        │ opaque application traffic
        ▼
local Minit gateway
        │ final authorization decision
        ▼
local app
```

Principles:

- private/local is the default
- direct connectivity first where practical; blind relay as fallback
- Minit infrastructure should not hold a universal TLS/private-access key
- local gateway remains final authority
- authentication should be based on user/device cryptographic identity, passkeys, or locally verifiable credentials
- remote commands must be signed/encrypted and replay-resistant before they exist

**Gate:** compromising Minit's relay/control service must not be sufficient to read private app traffic or fabricate privileged local actions.

## Step 4 — Launch the first managed service around reliability, not hosting

**Goal:** monetize the operational burden while keeping application compute local.

The first paid Minit Cloud should be deliberately small:

> **Encrypted off-device backup + fleet dashboard + health alerts**

Free/local remains useful by itself:

```text
minit deploy
local health/restart/logs
local secrets
snapshot/rollback
local encrypted backup
```

Managed value begins when a second machine or off-device coordination is useful:

```text
encrypted off-device backup
central status dashboard
alerts
multiple computers
recovery/migration assistance
```

Strong first conversion moment:

> **Your app stays local. Your backup doesn't have to.**

The backup is encrypted locally; Minit stores ciphertext and does not possess the decryption key.

**Gate:** a cloud outage must not stop local apps, and a cloud compromise must not disclose protected application content.

## Step 5 — Become the control plane for many user-owned computers

**Goal:** move from one person's local apps to small-team infrastructure.

The product starts becoming materially more valuable when users have:

```text
3 machines
12 apps
5 users
```

Likely managed capabilities:

- multi-machine fleet view
- team membership and app access policy
- backup/recovery policy
- audit trail
- alerts and operational history
- SSO / enterprise identity where needed
- resource and AI-cost policy

This is where Minit can become a real management SaaS rather than a local process utility.

**Business model:** charge for coordination, reliability, recovery, and team operations — not for application compute that the customer already owns.

## Step 6 — Make local software portable and resilient

**Goal:** a computer should be replaceable without making the application disposable.

Capabilities:

- machine-to-machine migration
- restore app + data + identity onto a new device
- recovery-key rotation
- optional replication across user-controlled machines
- backup freshness / rollback-attack protection
- eventually failover for applications that merit it

This turns "my PC is the server" from a liability into a manageable deployment model.

## Step 7 — Revisit Remix and distribution only after the foundation is trustworthy

Remix, discovery, marketplace, and creator monetization remain strategically interesting, but they are intentionally deferred.

A possible future flywheel is:

```text
AI creates small software
        ↓
Minit deploys it locally
        ↓
people actually use it
        ↓
software becomes portable/shareable
        ↓
Remix adapts it for another user/machine
```

But distribution should not outrun reliability and security. The near-term product is **not** an app marketplace; it is dependable local software operations.

## Strategic sequence

```text
1. Reliable local runtime
        ↓
2. Sandbox / protect the machine
        ↓
3. Private persistent connectivity
        ↓
4. Managed backup + dashboard + alerts
        ↓
5. Team / fleet control plane
        ↓
6. Migration / replication
        ↓
7. Remix / discovery / ecosystem
```

The key discipline is to avoid drifting into "small Vercel in the cloud." Minit can use **Local Vercel** as an analogy for the user experience while keeping a different architectural center:

> **Your machine runs it. Minit manages it.**
