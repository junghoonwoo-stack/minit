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
Minit: management · connectivity · encrypted coordination
```

If Minit later operates relay, identity, rendezvous, or backup infrastructure, those services should be designed so application plaintext and decryption keys are not required by the service.

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

Repeated usage is a natural signal that an app is becoming persistent software. Minit should eventually offer a persistent local mode at the right moment, based on local usage signals rather than mandatory server telemetry.

The intended distinction is:

```text
minit run     temporary local session
minit deploy  persistent local service
```

`minit deploy` should mean "keep this running on this machine," not "upload this application to Minit cloud."

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

## Encryption should be architectural

Encryption is not a checkbox added later. Anything that leaves the local machine should be designed around local key ownership.

Minit should use established cryptographic primitives and OS-backed secure storage. It should not invent a custom encryption scheme, and it should not claim zero-knowledge properties before those properties are implemented and reviewed.

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

## Category

**Local-first Micro IT** — small software that can be created and operated by one person or a small team, with Minit handling the management work around the local runtime.
