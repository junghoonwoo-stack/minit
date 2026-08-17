# Minit Business Model

Minit follows an open-source + hosted model inspired by successful developer infrastructure companies such as Supabase.

The principle is simple:

> **Make the core useful for free. Charge for operating the parts users no longer want to operate themselves.**

## 1. Minit OSS — free

The open-source core should remain genuinely useful:

- `minit run`
- local app discovery
- local PC as compute
- local app identity
- basic shareable endpoint
- self-hostable networking/relay components as they mature

A solo builder should be able to publish a small app without creating an account or paying Minit.

## 2. Minit Cloud — hosted convenience

The first paid layer should remove operational friction while the user's PC can still remain the compute:

- stable `*.minit.run` URL
- custom domains
- app identity synced to the cloud
- authentication / invite links
- usage and error logs
- analytics
- managed relay
- secrets and configuration sync

This is the natural first monetization point: the app has real users, so a stable identity and better operations become valuable.

## 3. Minit Managed — managed compute

When the user's PC is no longer enough:

```bash
minit move --managed
```

Minit should move the same application to managed compute while preserving its identity:

- same app
- same URL
- same users
- same configuration
- same secrets
- same logs

The user pays because the app has earned the need for uptime and capacity.

## 4. Minit Enterprise — later

For companies where many employees create small applications:

- SSO / OIDC
- company-only access
- app inventory
- audit logs
- security policies
- private relay
- ownership / offboarding
- admin controls

Enterprise is deliberately secondary to the solo-builder experience.

## Product funnel

```text
Local OSS
   ↓
Real users
   ↓
Minit Cloud
(stable URL, auth, logs)
   ↓
Minit Managed
(always-on compute)
   ↓
Team / Enterprise
```

Or more simply:

> **Local Free → Real Usage → Hosted Paid → Managed Paid**

## Why the local app identity matters

Every Minit project receives a persistent local app ID in `.minit/app.json`.

That identity is the bridge between open source and hosted services. The runtime can change from a laptop to managed infrastructure without forcing the user to recreate the application.

The moat is not the tunnel itself. The moat should become the **easiest lifecycle from localhost → real users → stable hosted app → managed app**, while preserving identity and minimizing infrastructure knowledge.
