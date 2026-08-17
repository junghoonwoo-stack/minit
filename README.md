# Minit

**Publish small apps from your own computer.**

> Think Replit Deployments, but your PC is the server.

Minit is an open-source lightweight runtime for turning a local app into a small team app without setting up a traditional server.

Build with Claude Code, Codex, Cursor, Replit, Lovable, or any framework you like. Run the app on your own computer, then use Minit to give 5–10 teammates a secure link.

```text
Local app → minit run → secure outbound tunnel → team URL
    ↑                                              ↓
 your PC                                    5–10 teammates
```

## Why Minit?

AI coding made software cheap to build. Deployment and operation are still surprisingly heavy.

A useful internal tool can be created in hours, but sharing it often turns into a server request, cloud account, firewall review, SSO integration, secrets management, deployment pipeline, and operations project.

Minit is for the gap between **"it works on my PC"** and **"let's make this an enterprise system."**

- No dedicated server for small tools
- Your computer remains the compute
- Share with a link
- Outbound connection only; no inbound firewall rule
- Basic authentication and allowlists
- TLS through the relay
- Stop the app when you are done
- If the PC reboots, just run it again

## The one-line explanation

**Minit is the open-source way to publish a small app directly from your own computer.**

Alternative shorthand:

> **Replit Deployments, but your PC is the server.**

## Who is it for?

### Individuals
You made a useful app locally and want a few people to use it without learning cloud infrastructure.

### Teams
A team needs small internal tools that are useful but not important enough to justify a production platform.

### Enterprises
Employees are building more software with AI. Minit provides a controlled path for small-team deployment with company authentication, policy, logging, and centrally managed relay infrastructure.

## Example

Your app already runs locally:

```bash
streamlit run app.py --server.port 8501
```

Publish it:

```bash
minit run --port 8501
```

Minit returns:

```text
✓ Local app: http://127.0.0.1:8501
✓ Team URL:  https://blue-panda.minit.run
✓ Access:    invite-only
✓ Compute:   this computer
```

Send the URL to your teammates. Your computer stays on while they use it.

## Product principles

1. **Local-first compute** — the app and its data can remain on the user's machine.
2. **Small-team by design** — optimize for 1–20 users, not internet-scale traffic.
3. **Zero-ops default** — no Docker, Kubernetes, VM, or cloud account required for the basic path.
4. **Safe enough by default** — TLS, authentication, access control, and audit metadata should be automatic.
5. **Graduate, don't scale forever** — when an app becomes mission-critical, move it to proper production infrastructure.
6. **Open-source core** — local agent and self-hostable relay remain available to everyone.

## Architecture

```text
                   ┌──────────────────────────┐
                   │       Minit Relay        │
                   │  OSS self-host / Cloud   │
                   └───────────┬──────────────┘
                               │ TLS
                         outbound tunnel
                               │
┌──────────────────────────────▼─────────────────────────────┐
│                       Your computer                        │
│                                                          │
│  App :8501  ◄──── Minit Agent ──── Auth / policy / logs   │
└───────────────────────────────────────────────────────────┘
                               ▲
                               │ https://*.minit.run
                               │
                   ┌───────────┴───────────┐
                   │     Team members      │
                   │       5–10 users      │
                   └───────────────────────┘
```

The local agent opens an **outbound** encrypted connection to a relay. Teammates connect to the relay URL; requests are forwarded through that connection to the local app. This avoids exposing a local listening port directly to the internet.

## Open source + hosted business model

### Minit OSS
Free and self-hostable:
- CLI / local agent
- Relay server
- Local configuration
- Basic invite / token access
- Basic request logs

### Minit Cloud
Paid convenience:
- Managed relay
- Stable `*.minit.run` URLs
- Identity / invite management
- Usage dashboard
- Longer log retention
- Managed updates

### Minit Enterprise
Paid control:
- Company SSO / OIDC
- Domain allowlists
- Central app registry
- Security policy templates
- Audit logs
- Private/company relay
- App ownership and offboarding
- Admin kill switch

The model is intentionally similar to successful open-source infrastructure businesses: make the core easy to adopt and self-host, then charge for operating the shared control plane and enterprise controls.

## What Minit is not

Minit is not intended to replace production cloud infrastructure.

Use something else when you need:
- 24×7 availability
- high traffic
- strong SLA
- internet-scale public services
- regulated production workloads requiring formal infrastructure controls

Minit exists so every useful 5-person tool does **not** have to start as a production IT project.

## Roadmap

### v0.1 — Local → Link
- [ ] `minit run --port <port>`
- [ ] outbound HTTP tunnel
- [ ] generated team URL
- [ ] access token / invite
- [ ] basic request log

### v0.2 — Team-ready
- [ ] email/domain allowlist
- [ ] local app registry
- [ ] restart/reconnect
- [ ] simple dashboard
- [ ] Windows/macOS packages

### v0.3 — Enterprise-ready
- [ ] OIDC / SSO
- [ ] organization policy
- [ ] audit logging
- [ ] centrally managed relay
- [ ] admin app inventory / kill switch

## Status

Early concept / prototype. The first goal is deliberately small:

> **Make a web app running on one PC usable by 5–10 people through one secure link.**

## License

Apache License 2.0. See [LICENSE](LICENSE).
