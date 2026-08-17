# Minit Product Thesis

## Thesis

AI coding dramatically reduces the cost of building software. The next bottleneck is deployment.

Minit is for the person who has a working app on their PC and wants real users to try it immediately — without learning cloud infrastructure first.

> **Your PC is the first server. Launch first. Cloud later.**

## Initial user

Someone who:
- built an app with Claude Code, Codex, Cursor, or similar tools
- has it working on localhost
- wants a few real users quickly
- does not know or care about server operations yet
- is willing to keep their PC on while testing demand

## Killer moment

```bash
minit run
```

Result:

```text
https://your-app.example.com
```

Copy the link. Send it to users. Learn.

## Lifecycle

```text
Local OSS → Real users → Minit Cloud → Minit Managed
```

The open-source product gets the user from localhost to real users. Hosted services become valuable only after real usage appears.

Minit Cloud adds stable identity, URLs, authentication, logs and managed networking. Minit Managed later moves the same app to always-on compute.

The key product promise is continuity: the app should not need to be rebuilt or re-platformed as it grows.

## Category

**Micro IT** — software small enough to be built, launched and initially operated by one person.

Teams and enterprises are a later extension of the same model, not the first target.
