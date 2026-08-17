# Minit

**From localhost to real users in one command.**

> **Your PC is the first server. Launch first. Cloud later.**

Minit is an open-source runtime for people who build apps with Claude Code, Codex, Cursor, or other AI coding tools and want to put them in front of real users immediately — without learning cloud infrastructure first.

You already have the app running on your computer. Minit turns that local app into a real web service with a shareable URL.

```text
AI coding → localhost → minit run → public/private URL → real users
                              ↑
                         your own PC
```

No cloud account. No VM. No server setup. No Docker required for the basic path.

Your PC provides the compute until the app proves it deserves something bigger.

## The problem

AI coding has made it possible for one person to build a working product in hours.

But the moment you want someone else to try it, a completely different set of questions appears:

- Where do I host this?
- What is a server?
- Do I need AWS, Azure, GCP, Vercel, or something else?
- How do I configure HTTPS and domains?
- How do I expose localhost safely?
- How do I manage API keys?
- How do I keep the service running?
- Why am I solving infrastructure problems before I even know whether anyone wants the product?

For an early product with 3, 10, or 30 users, this is often unnecessary overhead.

**Minit removes the cloud decision from day one.**

Use the computer that already runs the app. Publish it. Send a link. Learn from real users.

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

Minit gives you a live URL:

```text
✓ App detected: http://127.0.0.1:8501
✓ Live URL:     https://blue-panda.minit.run
✓ Compute:      this PC
```

Send the link to users.

That is the product loop:

> **Build → launch → share → observe → improve**

Keep your PC on while people use the app. If the PC is off, the service is off. At this stage, that is often fine.

Minit is designed for the moment when **speed of learning matters more than infrastructure perfection.**

## Who is Minit for?

### AI app builders

You built something with Claude Code, Codex, Cursor, or another AI coding tool. It works on localhost. Now you want someone outside your own computer to actually use it.

You should not need cloud expertise just to get that first feedback.

### Solo builders testing product-market fit

You do not know yet whether the product should exist, let alone how it should scale.

You want to get a handful of real users quickly, watch what they do, fix the product, and repeat.

Minit lets you postpone infrastructure decisions until there is evidence that they matter.

### Developers who simply want the shortest path from local to live

Even experienced developers do not always want to create cloud infrastructure for every prototype, demo, side project, agent, or experimental app.

Minit makes localhost shareable without making the builder become a hosting operator.

### Teams and enterprises — second

The same idea can later apply inside companies: an employee builds a useful app and wants five or ten colleagues to use it without turning it into a formal IT project.

Minit can add company authentication, policy, audit logs, private relays, and app registries. But the first product priority is simple:

> **Make it ridiculously easy for one person to get an app from localhost to real users.**

## The core idea: hosting before cloud

Most deployment platforms assume that publishing an app means moving it into cloud infrastructure.

Minit adds a step before that:

```text
Traditional path

Local app → cloud hosting → real users

Minit path

Local app → your PC as server → real users
                         ↓
                  managed hosting later
```

Your computer is already capable of running the app. For early usage, it can also be the first server.

Minit provides the missing layer that makes this practical: a secure URL, networking, access control, and a path to managed hosting later.

## Local first. Managed later.

Minit should not force users to pay for compute before they know whether the app has value.

Start here:

```text
Users
  ↓
Minit secure relay
  ↓
Your PC
  ↓
Your app
```

Your PC provides the compute. Minit makes it reachable.

Then something good happens:

- people keep using the app
- you want it available while your laptop is closed
- traffic grows
- you want a custom domain
- you need background jobs or persistent storage
- you no longer want to think about uptime

That is when hosting becomes valuable.

The transition should be one command or one button:

```bash
minit move --managed
```

Minit moves the application to managed compute while preserving, as much as possible:

- the same URL
- the same users
- the same app identity
- the same configuration
- the same secrets
- the same logs

**Launch first. Cloud later.**

Managed hosting should feel like an upgrade to a successful app, not a prerequisite for starting one.

## What makes Minit different?

### 1. Your PC is the first server

Most deployment tools start by asking where your app should run in the cloud.

Minit starts with a different question:

> **It already runs on your PC. Why move it yet?**

For the first few users, your existing machine may be all the infrastructure you need.

### 2. One command from localhost to live

The ideal experience is:

```bash
minit run
```

Minit should discover the local app, identify its port, establish a secure outbound connection, and return a URL.

No router configuration. No public IP. No inbound firewall setup.

### 3. Designed for AI-built apps

Claude Code, Codex, Cursor, and similar tools are creating a new class of builders who can make useful software without wanting to become infrastructure specialists.

Minit should automatically recognize common stacks these tools produce:

- Python
- FastAPI
- Flask
- Streamlit
- Gradio
- Node.js
- Next.js
- other common lightweight web stacks

Over time, Minit should also detect:

- how the app starts
- which port it uses
- required environment variables
- secrets
- local storage needs
- dependencies needed for managed migration

### 4. A seamless path to managed hosting

Minit is more than a temporary tunnel.

The long-term product is the lifecycle:

> **Local → Live → Used → Managed**

The moat is making that transition so easy that a builder never needs to re-platform just because the experiment became successful.

## Product principles

1. **One command to publish.** If the user needs infrastructure knowledge, we have failed.
2. **Your PC first.** Use the compute you already own before renting more.
3. **Real users before production architecture.** Validate demand first.
4. **Optimize for learning speed.** Early products need feedback more than uptime guarantees.
5. **No production theater.** A ten-user experiment does not need Kubernetes.
6. **Secure defaults.** TLS, safe networking, secrets, and basic access control should happen automatically.
7. **Open-source core.** Anyone should be able to run, inspect, self-host, and extend the core.
8. **Managed is earned.** Hosting becomes paid when the app has enough value that convenience and uptime matter.

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

The Minit Agent establishes an outbound encrypted connection to the relay. Users connect through the Minit URL, and traffic is forwarded to the app already running on your PC.

The user should not need to configure a public IP, port forwarding, or inbound firewall rules.

## Open source + hosted model

Minit should follow a simple adoption model:

> **Make starting free and effortless. Charge when the app becomes valuable enough that hosting is worth paying for.**

### Minit OSS

Free and open source:

- CLI / local agent
- self-hostable relay
- local configuration
- basic access control
- basic logs

Anyone should be able to run Minit themselves and understand how it works.

### Minit Cloud

Paid convenience as usage becomes real:

- managed relay
- stable `*.minit.run` URLs
- custom domains
- identity and invite management
- longer log retention
- managed secrets/configuration
- monitoring
- **one-click move from PC to managed compute**
- managed runtime when the builder no longer wants the PC to be the server

The natural funnel is:

```text
Local Free → Real Usage → Managed Paid
```

### Minit Enterprise

A later extension for organizations that want the same lightweight publishing model with central controls:

- SSO / OIDC
- company-only access
- security policies
- central app registry
- audit logs
- private relay
- app ownership/offboarding
- admin kill switch

## What Minit is not

Minit is not trying to make a laptop behave like an internet-scale production server.

Local mode is intentionally for experimentation, demos, early products, small audiences, and lightweight usage.

Move to managed infrastructure when you need:

- 24×7 availability
- more traffic than your PC comfortably handles
- background workloads
- stronger persistence
- production SLA
- formal operational controls

The key principle is:

> **You should not have to solve scale before you have demand.**

## Roadmap

### v0.1 — Localhost → live URL

- [ ] `minit run`
- [ ] automatic local port detection
- [ ] encrypted outbound tunnel
- [ ] generated `*.minit.run` URL
- [ ] public/private modes
- [ ] basic access token / invite
- [ ] request and error logs
- [ ] macOS / Windows support

### v0.2 — Zero-config publishing

- [ ] detect Python / Node projects
- [ ] detect common AI app frameworks
- [ ] detect launch command
- [ ] environment variable / secret detection
- [ ] stable app identity and URL
- [ ] simple usage dashboard
- [ ] custom domain support

### v0.3 — Local → Managed

- [ ] `minit move --managed`
- [ ] automatic dependency packaging
- [ ] secrets/config migration
- [ ] persistent URL and app identity
- [ ] managed runtime
- [ ] basic persistent storage options
- [ ] rollback / move between local and managed runtime

### Later — Teams & Enterprise

- [ ] email/domain allowlists
- [ ] OIDC / SSO
- [ ] organization policies
- [ ] audit logging
- [ ] private/company relay
- [ ] organization-wide app inventory

## The thesis

AI coding has dramatically reduced the cost of building software.

The next bottleneck is not coding. It is getting that software out of localhost and into the hands of real users.

Today, many builders jump directly from a local prototype into cloud infrastructure before they know whether anyone wants the product.

Minit introduces a simpler path:

> **Your PC is the first server.**

Build the app. Publish it. Give people the link. Learn.

If nobody uses it, shut it down.

If people love it, move it to managed hosting.

**Minit is the easiest path from localhost to real users — and from real usage to the cloud only when it matters.**

## Status

Early concept / prototype.

The first milestone is deliberately small:

> **Take a web app running on one PC and make it usable by real users through one command and one link.**

## License

Apache License 2.0. See [LICENSE](LICENSE).
