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

Development `main` supports streaming encrypted data backups:

```bash
minit backup create
minit backup list
minit backup verify <backup-id>
minit backup restore <backup-id>
```

If the managed app is running, backup creation temporarily stops it, streams `.minit/data` through tar+gzip directly into AES-256-GCM encryption, verifies the resulting ciphertext, and restarts the app.

No plaintext tar archive is intentionally written to disk by this path.

Encrypted `.mnb` backup objects are suitable for blind cloud storage because decryption keys remain local/user-controlled.

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

The cloud layer exists to remove tedious administration without becoming the app runtime.

First inspect exactly what is eligible to leave the device in cleartext:

```bash
minit cloud preview
```

Eligible metadata is deliberately narrow: opaque app/device IDs, health/status, restart/autostart state, CPU/RAM/process metrics, aggregate run/live-time statistics, and encrypted-backup status.

Not eligible in cleartext: app names, source code, commands, paths, filenames, application data, raw logs, prompts, user inputs/outputs, secrets, or decryption keys.

A development cloud admin service now exists under `cloud_service/`. It can be deployed to Railway or another container platform. It stores only allowlisted status metadata and already-encrypted `.mnb` backup objects.

Connect a local app:

```bash
minit cloud configure --url https://<admin-service>
```

The admin token is entered via a hidden prompt and stored in the approved local OS key store, not in the project file.

Send the current allowlisted operational snapshot:

```bash
minit cloud sync
```

Upload a locally verified encrypted backup:

```bash
minit cloud backup <backup-id>
```

The cloud server can store/return the ciphertext but does not possess the per-app key, backup data key, device root key, or user recovery key.

Automatic periodic status sync is deliberately still disabled. Explicit sync comes first so the privacy boundary is inspectable and testable before a background local management agent is introduced.

See `docs/CLOUD_ADMIN_PRIVACY.md` and `cloud_service/README.md`.

## Current focus

Near-term development is focused on making the local runtime private, simple, and reliable:

1. sandbox / filesystem and network boundaries
2. real-device autostart + OS key-store validation
3. separate local background admin agent for periodic privacy-safe status sync and backup scheduling
4. privacy-safe fleet/admin views and alerts
5. authenticated end-to-end remote administration where the server cannot fabricate privileged commands

Marketplace, discovery, monetization, and Remix are intentionally on hold while this foundation is built.
