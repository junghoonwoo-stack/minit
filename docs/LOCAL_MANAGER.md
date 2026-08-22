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

The device root key is expected to live in an approved OS-backed key store. Per-app keys are wrapped locally; secret values are encrypted locally.

## Source snapshots and rollback

```bash
minit snapshot create --label before-change
minit snapshot list
minit rollback <snapshot-id>
```

Snapshots are for source/config recovery after a bad AI edit. `.minit/data` is intentionally outside source rollback.

Rollback first creates a safety snapshot, restores source/config, and restarts a previously running managed service with a health check.

## Mutable data and encrypted backup

Minit exposes `.minit/data` to managed apps as `MINIT_DATA_DIR`.

Development `main` now supports streaming encrypted data backups:

```bash
minit backup create
minit backup list
minit backup verify <backup-id>
minit backup restore <backup-id>
```

If the managed app is running, backup creation temporarily stops it, streams `.minit/data` through tar+gzip directly into AES-256-GCM encryption, verifies the resulting ciphertext, and restarts the app.

No plaintext tar archive is intentionally written to disk by this path.

Encrypted `.mnb` backup objects are designed to be eligible for future blind cloud storage. Decryption keys remain local/user-controlled.

## User-held recovery

```bash
minit recovery create
minit recovery status
minit recovery restore
```

The recovery key is generated locally and shown to the user. Minit does not store that key. The local recovery envelope contains only the per-app key encrypted under the user-held recovery key.

## User-level autostart

After a service is configured, development `main` includes:

```bash
minit autostart install
minit autostart status
minit autostart remove
```

Adapters exist for macOS LaunchAgent, Linux systemd user services, and Windows Task Scheduler. Real-device login/reboot validation remains pending.

## Cloud administration without cloud ownership

The future cloud layer is intended to remove tedious administration without becoming the app runtime.

Use:

```bash
minit cloud preview
```

to inspect the complete cleartext status payload currently eligible for a future Minit admin service.

Eligible metadata is deliberately narrow: opaque app/device IDs, health/status, restart/autostart state, CPU/RAM/process metrics, aggregate run/live-time statistics, and encrypted-backup status.

Not eligible in cleartext: app names, source code, commands, paths, filenames, application data, raw logs, prompts, user inputs/outputs, secrets, or decryption keys.

No automatic cloud telemetry transport is configured yet.

See `docs/CLOUD_ADMIN_PRIVACY.md`.

## Current focus

Near-term development is focused on making the local runtime private, simple, and reliable:

1. sandbox / filesystem and network boundaries
2. real-device autostart + OS key-store validation
3. backup scheduling/retention and blind ciphertext upload
4. privacy-safe fleet/admin views
5. authenticated end-to-end remote administration where the server cannot fabricate privileged commands

Marketplace, discovery, monetization, and Remix are intentionally on hold while this foundation is built.
