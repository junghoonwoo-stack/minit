# Minit Product Thesis

## Thesis

AI coding dramatically reduces the cost of building small software. The next bottleneck is deployment and operation.

Traditional enterprise IT assumes applications are centralized, durable, and important enough to deserve dedicated infrastructure. AI coding creates a new class of software: small, useful, disposable or semi-permanent tools created by individuals for a handful of coworkers.

Minit provides infrastructure for that new class: **Micro IT**.

## Category

**Micro IT** — small applications, small audiences, local ownership, lightweight operations.

Minit is the runtime for Micro IT.

## Positioning

Primary description:

> **Minit is the open-source way to publish a small app directly from your own computer.**

Fast analogy:

> **Replit Deployments, but your PC is the server.**

Enterprise description:

> **A controlled local-to-team deployment layer for employee-built applications.**

## Why now

Before AI coding, writing the application was the expensive part. A company could justify centralized deployment because relatively few people created software.

With AI coding, thousands of employees can create useful tools. Requiring every 5-person tool to follow the same infrastructure path as a production enterprise system recreates the old IT bottleneck after development has already become cheap.

## Initial user

Someone who:
- has a working web app on their laptop/desktop
- wants 2–20 people to use it
- does not want to learn cloud deployment
- does not need 24×7 reliability
- is willing to keep their PC running while the tool is in use

## Killer moment

```bash
minit run --port 8501
```

Result:

```text
https://blue-panda.minit.run
```

Copy link. Send to team. Done.
