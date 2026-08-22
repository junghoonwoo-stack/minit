# Local Manager (development)

> This document describes features currently on `main` / `0.2.0.dev0`. They are not part of the published PyPI `0.1.0` release yet.

Minit is evolving from temporary local publishing into local-first application management:

> **Your machine runs it. Minit manages it.**

The application process, code, mutable data, secrets, and encryption keys remain on machines controlled by the user.

## Persistent local service

```bash
minit deploy --port 8000 -- python app.py
```

`minit deploy` does **not** upload the app. It starts a detached local supervisor and waits for the configured local HTTP port to become healthy.

Manage it with:

```bash
minit status
minit logs
minit restart
minit stop
```

The supervisor can restart a failed app and records local CPU/memory/process information. Runtime state and logs stay under `.minit/`.

## Minimal environment and local secrets

Minit-managed apps do not inherit arbitrary shell environment variables by default. This reduces accidental exposure of unrelated credentials from the user's terminal session.

Encrypted app secrets are managed explicitly:

```bash
minit security doctor
minit security init
minit secret set OPENAI_API_KEY
minit secret list
```

Secret values are entered through a hidden prompt. The device root key is intended to remain in an approved OS-backed key store, while per-app keys and secret values are stored on disk only as authenticated ciphertext.

## User-held recovery

```bash
minit recovery create
minit recovery status
minit recovery restore
```

`minit recovery create` prints a recovery key once. Minit does not upload or retain that recovery key. The local recovery envelope contains only a wrapped app key.

The user must keep the recovery key somewhere independent of the machine. Losing both the device key and the recovery key can make protected local material unrecoverable.

## Local snapshots and rollback

```bash
minit snapshot create --label before-change
minit snapshot list
minit rollback <snapshot-id>
```

The first snapshot implementation is deliberately conservative:

- it snapshots common source/config files
- `.minit/` is excluded entirely
- `.minit/data` is therefore never changed by rollback
- common non-source data such as databases/uploads are not treated as code versions
- rollback creates a safety snapshot first
- if the app was running, Minit restarts it and waits for a health result
- files created after the target snapshot are not deleted yet

This is not a replacement for application-aware database migrations or a full filesystem backup.

## User-level autostart

After a local service has been configured:

```bash
minit autostart install
minit autostart status
minit autostart remove
```

Current adapters target:

- macOS LaunchAgent
- Linux systemd user service
- Windows Task Scheduler `ONLOGON`

The generated autostart entry contains the project path and Minit supervisor command, not application secret values. Real-device validation remains required on each supported OS before this is treated as release-ready.

## Local filesystem protection

On POSIX systems Minit-managed state is written with owner-only permissions:

- `.minit/` directories: `0700`
- local state, logs, encrypted envelopes, snapshots: `0600`

Existing state can be re-hardened with:

```bash
minit security harden
```

Windows ACL hardening is a separate implementation item; Minit does not claim equivalent ACL enforcement there yet.

## Security boundary

These development features strengthen local operation, but they do not yet complete the long-term security model. In particular:

- arbitrary AI-generated apps are not yet strongly sandboxed from other same-user local processes
- persistent remote browser access with a blind relay / end-to-end session is not implemented
- encrypted remote backup storage is not implemented
- current `minit run` still uses Cloudflare Quick Tunnel and should not be treated as the future zero-server-plaintext architecture

See [THREAT_MODEL.md](THREAT_MODEL.md), [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md), and [CONNECTIVITY_AND_IDENTITY.md](CONNECTIVITY_AND_IDENTITY.md).
