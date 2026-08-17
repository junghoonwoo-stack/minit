# Minit

**From localhost to real users in one command.**

> **Your PC is the first server. Launch first. Cloud later.**

Minit is an open-source runtime for people who build apps with Claude Code, Codex, Cursor, or other AI coding tools and want real users to try them immediately — without learning cloud infrastructure first.

```text
AI coding → localhost → minit run → public URL → real users
                              ↑
                         your own PC
```

No VM. No cloud account. No Docker required for the basic path.

## MVP: it works today

Minit v0.1 uses **Cloudflare Quick Tunnel** as the temporary transport layer. Your app still runs entirely on your PC; Minit launches the tunnel and gives you a shareable URL.

### 1. Install Minit

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

### 2. Install `cloudflared`

macOS:

```bash
brew install cloudflared
```

Windows:

```powershell
winget install --id Cloudflare.cloudflared
```

Linux: install `cloudflared` using Cloudflare's official package for your distribution.

### 3. Start any local web app

For example:

```bash
streamlit run app.py
# or
python app.py
# or
npm run dev
```

### 4. Publish it

```bash
minit run
```

Minit scans common local ports. You can also specify one explicitly:

```bash
minit run --port 8501
```

You will get output like:

```text
✓ Local app: http://127.0.0.1:8501 (200)
→ Creating public link...

✓ Live URL: https://tiny-cat-123.trycloudflare.com
✓ Compute:  this PC
✓ Status:   live while this terminal and PC stay on

Send the URL to your first users.
Press Ctrl+C to stop publishing.
```

That is the whole MVP.

## Why Minit?

AI coding made software cheap to build. The next bottleneck is getting it out of localhost.

A solo builder should not have to learn AWS, Azure, GCP, Vercel, containers, DNS, TLS, or server operations before discovering whether ten people even want the product.

Minit adds a stage before cloud hosting:

```text
Traditional
Local app → cloud hosting → users

Minit
Local app → your PC as server → users
                         ↓
                  managed hosting later
```

The product loop is:

> **Build → launch → share → observe → improve**

If nobody uses the app, turn it off.

If people love it, then hosting becomes worth paying for.

## Local first. Managed later.

The long-term Minit lifecycle is:

```text
Local Free → Real Usage → Managed Paid
```

Initially:

```text
Users
  ↓
Minit relay
  ↓
Your PC
  ↓
Your app
```

Later, when you want 24×7 uptime or your PC is no longer enough:

```bash
minit move --managed
```

The goal is to move the app to Minit-managed compute while preserving its URL, users, configuration, secrets, logs, and identity.

**Managed hosting is an upgrade for a successful app, not a prerequisite for starting one.**

## What Minit owns vs. the MVP transport

Today, Cloudflare Quick Tunnel supplies the public tunnel so Minit can validate the user experience quickly.

Minit owns the higher-level workflow:

- discover the local app
- validate that it is reachable
- create a shareable endpoint
- keep the user's PC as compute
- make publishing one command
- eventually preserve app identity across Local → Managed

The roadmap is to replace the temporary transport dependency with a Minit relay and stable `*.minit.run` app identity.

## Commands

Check your machine:

```bash
minit doctor
```

Publish an auto-detected local app:

```bash
minit run
```

Publish a specific port:

```bash
minit run --port 3000
```

Stop publishing with `Ctrl+C`.

## Product principles

1. **One command to publish.** Infrastructure knowledge should be optional.
2. **Your PC first.** Use compute you already own.
3. **Real users before production architecture.** Validate demand first.
4. **Optimize for learning speed, not uptime.**
5. **Open-source core.** Anyone can inspect and extend Minit.
6. **Managed is earned.** Pay for hosting only after usage makes it valuable.
7. **Local → Managed without re-platforming.** This migration path is a core product moat.

## Roadmap

### v0.1 — working MVP

- [x] `minit run`
- [x] common local port auto-detection
- [x] local HTTP health check
- [x] outbound tunnel through Cloudflare Quick Tunnel
- [x] automatically capture and display the public URL
- [x] clean Ctrl+C shutdown
- [x] `minit doctor`
- [ ] automatic `cloudflared` installation
- [ ] packaged Windows/macOS installer

### v0.2 — Minit identity

- [ ] stable app identity
- [ ] `*.minit.run` URLs
- [ ] public/private modes
- [ ] invite links / lightweight auth
- [ ] request and error logs
- [ ] basic usage dashboard

### v0.3 — zero-config AI app publishing

- [ ] detect Python / Node projects
- [ ] detect Streamlit / FastAPI / Flask / Gradio / Next.js
- [ ] detect launch command
- [ ] detect ports automatically beyond common ports
- [ ] environment variable / secret discovery
- [ ] local app manifest

### v0.4 — Local → Managed

- [ ] `minit move --managed`
- [ ] package dependencies automatically
- [ ] migrate configuration and secrets
- [ ] preserve URL and app identity
- [ ] managed compute
- [ ] move back to local when desired

### Later — teams and enterprises

- [ ] SSO / OIDC
- [ ] company-only access
- [ ] audit logs
- [ ] private relay
- [ ] app registry and policy

## Development

```bash
pip install -e '.[dev]'
pytest
```

## Status

Minit is an early prototype. The first milestone is deliberately narrow:

> **Take a web app running on one PC and put it in front of real users through one command and one link.**

## License

Apache License 2.0.
