# Minit Product Thesis

## Thesis

AI coding dramatically reduces the cost of building software. The next bottleneck is getting what works on localhost in front of real people — and then keeping the few successful experiments alive.

Minit is for the person who has a working app on their PC and wants real users to try it immediately, without learning cloud infrastructure first.

> **Your PC is the first server. Launch first. Pay when it matters.**

## Initial user

Someone who:

- built an app with Claude Code, Codex, Cursor, or similar tools
- has it working on localhost
- wants a few real users quickly
- does not know or care about server operations yet
- is willing to keep their PC on while testing demand

## First killer moment

```bash
minit run
```

Result:

```text
https://temporary-public-url.example
```

Copy the link. Send it to users. Learn.

## Second killer moment

If the app matters enough that the builder no longer wants their PC to be the server:

```bash
minit deploy
```

The target promise is:

> **Keep this app online without your PC.**

The same app identity should move from local runtime to managed runtime without forcing a new infrastructure project.

## Lifecycle

```text
Local app
   ↓
minit run
   ↓
Real users
   ↓
Usage proves the app matters
   ↓
minit deploy
   ↓
Managed runtime
```

The open-source product gets the user from localhost to real users. The managed service becomes valuable only after real usage creates an uptime or operations need.

## Continuity

The key product promise is continuity:

```text
same app
same identity
same workflow
local → managed
```

This is why the persistent `.minit/app.json` identity exists.

## Category

**Micro IT** — software small enough to be built, launched, and initially operated by one person.

Teams and enterprises are a later extension of the same lifecycle, not the first target.
