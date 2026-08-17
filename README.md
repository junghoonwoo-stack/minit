# Minit

**Turn a local AI-built app into a live web service — from your own PC.**

> Build with Claude Code, Codex, Cursor, or your favorite AI coding tool. Run it on your PC. Share one link. See if anyone actually wants it.

Minit is an open-source runtime for people who can build software with AI but do not want to become cloud or server operators just to test an idea.

You already have an app working on your laptop. Minit makes the next step simple:

```text
AI coding → local app → minit run → public/private URL → real users
                            ↑
                       your own PC
```

No VM. No Docker required. No cloud account. No server setup.

Your PC is the server until you need something bigger.

## Why Minit?

AI coding has made it dramatically easier for one person to build a working product.

But the moment you want someone else to use it, the experience changes:

- Where do I host this?
- What is a server?
- Do I need AWS, Azure, or GCP?
- How do I configure HTTPS and domains?
- How do I keep API keys safe?
- How do I let only a few people in?
- What happens when the app becomes popular?

For many early products, this infrastructure is unnecessary.

If you are testing an idea with 3, 10, or 30 users, the computer that already runs the app may be enough.

**Minit lets you start there.**

## The simplest possible workflow

Your app is already running locally:

```bash
python app.py
# or
streamlit run app.py
# or
npm run dev
```

Then:

```bash
minit run
```

Minit gives you a URL:

```text
✓ App detected: http://127.0.0.1:8501
✓ Live URL:     https://blue-panda.minit.run
✓ Compute:      this PC
```

Send the link to users.

Keep your PC on while they use the app. If your PC is off, the service is off. That is okay — Minit is designed for the stage where speed of learning matters more than infrastructure perfection.

## Who is Minit for?

### 1. AI app builders

You built something with Claude Code, Codex, Cursor, or another AI coding tool and it works on your machine.

Now you want real people to try it without first learning cloud infrastructure.

### 2. People testing product-market fit

You do not know yet whether your app deserves a production architecture.

You want to:

**build → publish → send a link → observe users → improve**

as quickly as possible.

### 3. Small teams and enterprises — later

The same problem exists inside companies: employees create useful AI-built tools, but even a five-person deployment can trigger a full IT process.

Minit can eventually provide company authentication, policy, audit logs, private relays, and app registries. This is an important use case, but the first priority is making Minit exceptionally easy for individual builders.

## Local first. Managed when needed.

Minit should not force users into hosting before their product needs hosting.

Start with:

```text
Users
  ↓
Minit secure relay
  ↓
Your PC
  ↓
Your app
```

Your PC provides the compute. Minit only makes it safely reachable.

If the app grows, your PC becomes inconvenient, or you need 24×7 availability:

```text
minit move --managed
```

The goal is for Minit to move the same app to managed infrastructure while keeping the important things unchanged:

- same URL
- same users
- same secrets/configuration
- same logs
- same app identity

**Start on your PC. Move to managed hosting only when the product earns it.**

## What makes Minit different?

### Your PC is a valid first server

Most deployment products assume cloud infrastructure from day one. Minit assumes that early software is small, uncertain, and changing quickly.

### Built for AI-generated apps

Minit should automatically understand common projects created by AI coding tools: Python, FastAPI, Flask, Streamlit, Gradio, Node.js, Next.js, and similar stacks.

The long-term goal is simple:

```bash
minit run
```

Minit discovers how the app runs, finds its port, identifies required environment variables, and publishes it with minimal configuration.

### A natural path from local to production

Minit is not only a tunnel. It should preserve the application's identity and configuration so that moving from a laptop to managed infrastructure feels like changing the runtime, not rebuilding the product.

That portability is a core product principle.

## Product principles

1. **One command to publish.** If deployment requires infrastructure knowledge, we have failed.
2. **Local-first.** Use the machine you already own before renting another one.
3. **Optimize for learning speed.** Early products need user feedback more than high availability.
4. **No production theater.** A five-user experiment does not need Kubernetes.
5. **Secure defaults.** TLS, secrets, basic access control, and safe networking should happen automatically.
6. **Open-source core.** Anyone should be able to run and understand the core system.
7. **Managed is an upgrade, not a prerequisite.** Pay for hosting when the app has earned the need for it.

## Architecture

```text
                         Internet
                            │
                  https://*.minit.run
                            │
                   ┌────────▼────────┐
                   │   Minit Relay   │
                   └────────┬────────┘
                            │ encrypted outbound connection
                            │
              ┌─────────────▼─────────────┐
              │         Your PC           │
              │                           │
              │ Minit Agent → Local App   │
              │               :3000/:8000 │
              └───────────────────────────┘
```

The Minit Agent establishes an outbound encrypted connection. Users connect through the Minit URL, and traffic is forwarded to the app already running on your PC.

The user should not need to configure a public IP address, router port forwarding, or inbound firewall rules.

## Open source + hosted model

### Minit OSS

Free and open source:

- CLI / local agent
- self-hostable relay
- local configuration
- basic access control
- basic logs

This should be enough for anyone to understand Minit, run it themselves, and build on top of it.

### Minit Cloud

Paid when convenience starts to matter:

- managed relay
- stable `*.minit.run` URLs
- custom domains
- identity and invite management
- longer log retention
- managed secrets/configuration
- **one-click move from PC to managed compute**

### Minit Enterprise

For organizations that want the same lightweight deployment model with central control:

- SSO / OIDC
- company-only access
- security policies
- central app registry
- audit logs
- private relay
- app ownership/offboarding
- admin kill switch

## What Minit is not

Minit is not trying to make your laptop an internet-scale production server.

Local mode is intentionally optimized for experimentation and small usage.

Move to managed infrastructure when you need:

- 24×7 availability
- more traffic than your PC comfortably handles
- production SLA
- stronger operational controls
- always-on background workloads

The important part is that **you should not have to solve those problems before you have users.**

## Roadmap

### v0.1 — Local app → live URL

- [ ] `minit run`
- [ ] automatic local port detection
- [ ] encrypted outbound tunnel
- [ ] generated `*.minit.run` URL
- [ ] basic access token / invite
- [ ] basic request and error logs
- [ ] macOS / Windows support

### v0.2 — Zero-config AI app publishing

- [ ] detect Python / Node projects
- [ ] detect common AI app frameworks
- [ ] environment variable / secret detection
- [ ] app manifest generated automatically
- [ ] stable app identity and URL
- [ ] simple web dashboard

### v0.3 — Local → Managed

- [ ] `minit move --managed`
- [ ] automatic dependency packaging
- [ ] secrets/config migration
- [ ] persistent URL and app identity
- [ ] managed runtime
- [ ] rollback to local / previous version

### Later — Teams & Enterprise

- [ ] email/domain allowlists
- [ ] OIDC / SSO
- [ ] organization policies
- [ ] audit logging
- [ ] private/company relay
- [ ] organization-wide app inventory

## The thesis

AI coding is unbundling software development from professional software engineering teams.

The next bottleneck is deployment.

A person who can create a useful application in an afternoon should not need to become a cloud engineer before showing it to ten users.

**Minit makes the user's own computer the first deployment platform — and provides the easiest path to managed hosting when the application grows.**

## Status

Early concept / prototype.

The first milestone is deliberately small:

> **Take an AI-built web app running on one PC and make it usable by real users through one command and one link.**

## License

Apache License 2.0. See [LICENSE](LICENSE).
