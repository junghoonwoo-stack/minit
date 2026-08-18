# Minit Business Model

Minit should monetize only after the user's app has earned the need for infrastructure.

> **Launch first. Pay when it matters.**

The core journey is intentionally simple:

```text
AI coding / local app
        ↓
     minit run
        ↓
 temporary public URL
        ↓
   real users try it
        ↓
"I need this to stay online"
        ↓
    minit deploy
        ↓
   Minit Managed
```

## 1. Minit OSS — free

`minit run` remains genuinely useful without an account or payment.

- run the app on your own PC
- publish a temporary public URL
- persistent local app identity
- minimal setup and dependencies
- no Minit account required

The user's PC is the first server. If the experiment does not matter, they can stop it and pay nothing.

## 2. The natural conversion moment

Minit should not ask users to upgrade merely because they installed the CLI.

Paid intent appears when real usage creates operational pain:

- the PC must stay on
- the temporary URL is no longer enough
- the app needs predictable uptime
- the builder wants authentication, logs, secrets, or a custom domain

The product language should describe the job, not the purchase:

> **Keep this app online.**

> **Run without your PC.**

The CLI transition should eventually be:

```bash
minit deploy
```

Only at this point should account creation and payment become necessary.

## 3. Minit Managed — paid

`minit deploy` should promote the same app from local runtime to managed runtime without forcing the user to rebuild or re-platform it.

The first managed product should focus on:

- always-on managed compute
- stable URL
- automatic restart / health checks
- logs
- secrets and configuration
- simple authentication
- custom domain support

The key promise is continuity:

```text
same app ID
same project
same workflow
runtime: local → managed
```

The user is paying for operations they no longer want their laptop to provide.

## 4. Enterprise — later

Enterprise capabilities should be added only after the individual-builder workflow is proven.

Possible later capabilities:

- team ownership
- SSO / OIDC
- private networking
- app inventory
- audit logs
- policy controls
- offboarding and ownership transfer

These should not complicate the OSS product today.

## Open-source / commercial boundary

The public repository should remain the open-source local runtime and CLI.

A future hosted control plane, managed compute orchestration, billing system, and commercial service operations can live behind a service API and do not need to be part of the open-source repository.

This keeps the promise clear:

- **Minit OSS:** localhost → real users
- **Minit Managed:** real users → always online

## Licensing strategy

The OSS code is licensed under Apache License 2.0. This is intentionally permissive to reduce adoption friction.

A future managed service can be governed by separate commercial service terms while continuing to use the Apache-licensed CLI and local runtime.

Apache-2.0 does not create exclusivity around the source code. The durable advantage therefore needs to come from the product lifecycle, developer experience, managed service, ecosystem, trust, and brand — not from preventing forks.

## Build gates

Do not build the full managed platform merely because the business model is plausible.

Advance when users create the signal:

1. **OSS proof:** independent users successfully run `minit run`.
2. **Repeat proof:** users use Minit for a second app or session.
3. **Managed-intent proof:** users repeatedly ask for uptime, stable URLs, auth, or a way to run without their PC.
4. **Paid beta:** implement the smallest `minit deploy` path that solves the dominant request.
5. **Scale:** add reliability, billing, domains, auth, and team features only as usage requires them.

The most important early metric is not stars. It is:

> **How many people who are not the author successfully go from localhost → public URL → real user → repeat use?**
