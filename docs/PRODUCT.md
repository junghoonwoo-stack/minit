# Minit Product Principles

Minit starts with a simple job:

> **Deploy software to the computer you already own, and make that local runtime easy to operate.**

Minit is not primarily a cloud hosting product. The local machine is the application server; Minit provides the management layer around it.

## Local first

Your app, code, data, secrets, keys, and compute stay on a machine you control unless you explicitly choose otherwise.

> **Your PC is the server.**

The product should make that local runtime feel operationally boring: start, keep alive, monitor, recover, back up, share, and move it without requiring the user to become a server administrator.

## The core primitive is local deployment

The primary product path is:

```text
AI coding / local project
        ↓
    minit deploy
        ↓
app runs persistently on this computer
        ↓
Minit manages lifecycle / health / version / backup
        ↓
optional sharing and cloud administration
```

`minit deploy` means:

> **Keep this app running on this machine.**

It must not silently mean:

> Upload this application to Minit cloud.

The local machine remains the execution authority.

## `run` and `deploy` are different jobs

```text
minit deploy  persistent local service on this computer
minit run     temporary external sharing of an already-running local app
```

`minit run` remains useful for prototypes, demos, and first users. It should stay simple and should not require a Minit account.

`minit deploy` is the long-term center of the product because it turns an ordinary user-controlled computer into a manageable application runtime.

## Local control is the default

The product boundary is:

```text
Your machine: code · data · secrets · keys · execution
Minit cloud: aggregate administration · coordination · ciphertext storage
```

If Minit operates relay, identity, rendezvous, monitoring, or backup infrastructure, those services should be designed so application plaintext and decryption keys are not required by the service.

A compromise of Minit-operated infrastructure may affect availability and expose deliberately retained operational metadata. It must not by itself reveal customer application plaintext or provide cryptographic authority over a local runtime.

## Private by architecture

Code, mutable data, raw logs, prompts, user inputs/outputs, secret values, and decryption keys are local by default.

The cloud administration layer may receive a deliberately narrow set of aggregate operational metadata such as health, resource use, restart counts, aggregate usage, and encrypted-backup status. The exact cleartext contract must be inspectable and allowlisted in code.

Encrypted backup objects may be stored remotely, but backup data keys and recovery keys must remain user-controlled.

See [Cloud Administration Privacy Boundary](CLOUD_ADMIN_PRIVACY.md).

## Work with what already runs

Minit is not an application framework. If software already works locally, Minit should manage around it rather than forcing a migration into a proprietary runtime.

Claude Code, Codex, Cursor, and other tools may create the application. Minit should not require them to target a special Minit framework merely to become manageable.

## Management, not hosting

The long-term management surface is organized around eight verbs:

- **Run** — lifecycle, restart, health, boot persistence
- **Connect** — secure public/private access
- **Protect** — sandboxing, permissions, secrets, limits
- **Observe** — users, health, logs, resources, AI cost
- **Version** — snapshots and rollback
- **Backup** — encrypted recovery copies
- **Share** — people, teams, access policy
- **Move** — migration between user-controlled machines

The local manager remains the execution authority even when a cloud dashboard is used for administration.

## Cloud should remove administration, not ownership

The cloud layer exists to remove tedious operations from the user: fleet overview, health summaries, backup status, alerts, scheduling, and future remote administration.

It must not become the place where the application needs to live in order to function.

A useful mental model is:

```text
local machine = runtime + source of truth
cloud          = admin window + blind storage/relay
```

If the cloud service is unavailable, locally deployed apps should continue running.

## Encryption should be architectural

Encryption is not a checkbox added later. Anything sensitive that leaves the local machine should be designed around local key ownership.

Minit should use established cryptographic primitives and OS-backed secure storage. It should not claim zero-knowledge properties before those properties are implemented and reviewed.

## Recovery is part of encryption UX

If Minit cannot decrypt user backups, losing local keys can also mean losing recovery access. Key recovery, device replacement, and team recovery therefore belong in the product design from the beginning.

## Explicit security

Running AI-generated software on a personal or work computer changes the security boundary of that machine. Minit must make permissions explicit and progressively isolate apps from unrelated user files, credentials, other Minit apps, and OS key material.

Temporary public sharing also changes the network boundary. An unguessable URL is not authentication.

See [SECURITY.md](../SECURITY.md).

## Small dependency footprint

Installation and first run should require as little system knowledge and setup as practical. Infrastructure details stay out of the way unless the user needs them.

## Transparent and portable

Networking, relay, backup storage, and other infrastructure providers are implementation details. They should remain replaceable.

The persistent local app identity is the continuity anchor across runs, versions, backups, and future machine migration.

## Current product focus

The near-term goal is intentionally narrow:

> **Make deploying and operating AI-built apps on your own computer private, simple, reliable, and boring.**

Priority is local runtime reliability, sandboxing, monitoring, rollback, encrypted backup, recovery, and privacy-safe administration.

Public marketplace, discovery, creator monetization, and **Remix are deliberately on hold** until the local runtime/management foundation is dependable.

## Category

**Local-first application runtime and management** — software runs on user-controlled computers while Minit removes the operational work around that runtime.

For small-team and long-tail software, this is also the basis for **Local-first Micro IT**.