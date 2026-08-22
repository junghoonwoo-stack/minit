# Minit Architecture

Minit is local-first: application compute stays on a machine the user controls.

The long-term design goal is simple:

> **Your machine runs it. Minit manages it.**

Minit should make local software manageable without turning the application itself into a hosted cloud workload.

## Today: temporary local publishing

The current `minit run` path is:

```text
remote user
    │
    ▼
public HTTPS URL
    │
    ▼
Cloudflare Quick Tunnel
    │
    ▼
Minit on your computer
    │
    ▼
127.0.0.1:<your-port>
    │
    ▼
your web app
```

The application process and compute stay on your computer. Cloudflare is currently used as a connectivity transport, not as the application runtime.

Minit does not currently run a hosted application server, account system, backup service, or remote administration service for this flow.

## What `minit run` does today

1. Uses the port you provide, or checks a small set of common local development ports.
2. Confirms that something is listening on `127.0.0.1:<port>`.
3. Sends a local HTTP request as a basic health check.
4. Creates a persistent local Minit app identity in `.minit/app.json` if needed.
5. Finds a compatible `cloudflared` binary or downloads a pinned version.
6. Verifies downloaded helper binaries against an expected SHA256 digest before execution.
7. Starts a temporary tunnel pointing at the local app.
8. Waits briefly for the generated public URL to become reachable.
9. Keeps the path alive until the Minit process is stopped.
10. Records basic publish history locally so future management features do not require telemetry.

## Direction: local runtime + management

Minit should evolve around three layers:

```text
┌──────────────────────────────────────┐
│ Optional coordination / relay plane  │
│ routing · rendezvous · encrypted     │
│ backup blobs · minimal metadata      │
└──────────────────▲───────────────────┘
                   │ ciphertext / routing
                   │
┌──────────────────┴───────────────────┐
│        Minit Local Manager           │
│ lifecycle · permissions · keys       │
│ logs · usage · snapshots · backup    │
│ rollback · sharing · migration       │
└──────────────────▲───────────────────┘
                   │
┌──────────────────┴───────────────────┐
│          Local Runtime               │
│ app · agent · files · DB · models    │
│         user's machine               │
└──────────────────────────────────────┘
```

The local manager is the authority. A remote service, if used, is coordination infrastructure rather than the owner of the application.

## Local authority

The intended source-of-truth model is:

- application code stays local
- application data stays local by default
- secrets stay local
- decryption keys stay local
- execution policy is decided locally
- remote commands must ultimately be authorized and executed locally

A future Minit service should not require possession of application plaintext in order to route traffic, coordinate devices, or store encrypted backups.

## Encryption boundary

The target security model is end-to-end encryption for data that leaves the machine.

Conceptually:

```text
local root key
    │
    ├─ app key
    │    ├─ encrypted backup
    │    ├─ encrypted remote command
    │    └─ encrypted shared state
    │
    └─ recovery material
```

Keys should be generated locally and stored using platform-appropriate secure storage where possible. Minit should not invent custom cryptography; implementation should use established cryptographic libraries and operating-system key stores.

A coordination server may still need limited metadata such as device/app identifiers, online state, timestamps, routing information, and ciphertext sizes. The precise privacy claim should therefore be:

> **Minit should not be able to read application code, data, secrets, logs, or backups sent through its coordination services.**

This target is not yet fully implemented and should not be presented as a current product guarantee.

## Management surface

The local manager is expected to own eight capabilities over time:

1. **Run** — process lifecycle, restart, health checks, boot persistence.
2. **Connect** — public/private connectivity with replaceable transports.
3. **Protect** — sandboxing, permissions, secret handling, resource limits.
4. **Observe** — usage, health, resource consumption, logs, AI cost.
5. **Version** — snapshots, history, diff, rollback.
6. **Backup** — locally encrypted backups and recovery.
7. **Share** — users, teams, access policy, encrypted authorization.
8. **Move** — machine-to-machine migration and later replication.

## Local app identity

Each project has a persistent local manifest. The schema is intentionally additive and backward-compatible.

Example:

```json
{
  "schema_version": 1,
  "id": "persistent-uuid",
  "name": "my-app",
  "runtime": "local",
  "provider": "auto",
  "publish_history": {
    "successful_runs": 2,
    "total_live_seconds": 1800
  }
}
```

The app ID is independent of a particular URL or connectivity provider. It is the continuity anchor for future lifecycle, version, backup, and machine-migration features.

## Why keep management signals local?

Repeated local usage is itself a useful signal: a temporary app may be becoming persistent software.

Minit can detect this from local history without sending usage telemetry to a server. The current code contains this local decision primitive, but no persistent-service suggestion is shown until a real local deployment path exists.

## Networking is replaceable

Cloudflare Quick Tunnel is useful for the current MVP because it provides temporary HTTPS connectivity without signup or DNS configuration.

The long-term connectivity policy should be:

```text
direct connection when practical
          ↓
relay only when needed
```

Transport choice must remain separable from the local runtime and local management model.

## What Minit does not do today

Minit does not currently:

- install an application as an OS-level persistent background service
- sandbox application processes
- provide stable URLs across restarts
- provide encrypted remote administration
- encrypt and upload backups
- provide automatic rollback
- provide multi-device migration
- add authentication to arbitrary applications

Those features should be added incrementally, with the local machine remaining authoritative.

See [SECURITY.md](../SECURITY.md) before publishing anything sensitive.
