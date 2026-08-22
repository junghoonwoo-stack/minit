# Minit Product Principles

Minit starts with a simple job:

> **Take software that already works locally and make it easy to use and manage without moving the application into cloud compute.**

## Local first

Your app, code, data, and compute stay on a machine you control unless you explicitly choose otherwise.

> **Your PC is the first server.**

The product should make that local runtime feel operationally boring: start, share, monitor, recover, and move it without requiring the user to become a server administrator.

## Local control is the default

The long-term product boundary is:

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

## No account for the core local workflow

The basic path remains:

```text
build → localhost → minit run → shareable URL → feedback
```

`minit run` should not require a Minit account.

## Work with what already runs

Minit is not an application framework. If software already works locally, Minit should manage around it rather than forcing a migration into a proprietary runtime.

## Temporary first, persistent when useful

`minit run` is intentionally temporary. It is appropriate for prototypes, demos, and first users.

Repeated usage is a natural signal that an app is becoming persistent software. Minit should offer a persistent local mode at the right moment, based on local usage signals rather than mandatory server telemetry.

The distinction is:

```text
minit run     temporary local session
minit deploy  persistent local service
```

`minit deploy` means "keep this running on this machine," not "upload this application to Minit cloud."

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

## Encryption should be architectural

Encryption is not a checkbox added later. Anything sensitive that leaves the local machine should be designed around local key ownership.

Minit should use established cryptographic primitives and OS-backed secure storage. It should not claim zero-knowledge properties before those properties are implemented and reviewed.

## Recovery is part of encryption UX

If Minit cannot decrypt user backups, losing local keys can also mean losing recovery access. Key recovery, device replacement, and team recovery therefore belong in the product design from the beginning.

## Explicit security

Publishing localhost changes the security boundary of an application. Minit should make that visible, avoid pretending that an unguessable URL is authentication, and keep security-sensitive behavior explicit.

See [SECURITY.md](../SECURITY.md).

## Small dependency footprint

Installation and first run should require as little system knowledge and setup as practical. Infrastructure details stay out of the way unless the user needs them.

## Transparent and portable

Networking, relay, backup storage, and other infrastructure providers are implementation details. They should remain replaceable.

The persistent local app identity is the continuity anchor across runs, versions, backups, and future machine migration.

## Current product focus

The near-term goal is intentionally narrow:

> **Make locally running AI-built apps private, simple, reliable, and boring to operate.**

Priority is local runtime reliability, sandboxing, monitoring, rollback, encrypted backup, recovery, and privacy-safe administration.

Public marketplace, discovery, creator monetization, and **Remix are deliberately on hold** until the local runtime/management foundation is dependable.

## Category

**Local-first Micro IT** — small software that can be created and operated by one person or a small team, with Minit handling the management work around the local runtime.
