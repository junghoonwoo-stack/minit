# Local Manager (development)

> This document describes features currently on `main` / `0.2.0.dev0`. They are not part of the published PyPI `0.1.0` release yet.

Minit is evolving from temporary local publishing into local-first application management:

> **Your machine runs it. Minit manages it.**

The application process, code, mutable data, secrets, and encryption keys remain on machines controlled by the user.

## One-command persistent local deployment

For common web projects, start with:

```bash
minit deploy
```

Minit performs conservative local detection and currently recognizes common patterns including static `index.html`, FastAPI, Flask, Streamlit, Vite, Next.js, and an existing `.minit/service.json` configuration.

Detection is intentionally fail-closed. If Minit cannot safely determine both the application command and listening port, it does not guess. Configure the service explicitly once:

```bash
minit deploy --port 8000 -- python app.py
```

The resulting configuration is then reusable by later `minit deploy` calls.

`minit deploy` does **not** upload the app. It starts a detached local supervisor and waits for the configured local HTTP port to become healthy.

## Global local app registry

A successful deployment registers a small local locator under the user's Minit home directory so many apps can be managed without first changing into each project directory.

```bash
minit ls
```

Then, from another directory:

```bash
minit status my-app
minit logs my-app
minit restart my-app
minit stop my-app
```

Targets may be an app name, exact app ID, or an unambiguous app-ID prefix.

The registry is local-only and deliberately narrow. It stores app ID, app name, project directory, port, and registration timestamps. It does not copy application data, commands, secret values, encrypted secret envelopes, or raw logs into the registry or into Minit cloud.

A missing registered project is reported rather than silently removed because the project may be on a temporarily unavailable drive.

The supervisor can restart a failed app and records local CPU/memory/process information. Runtime state and logs remain under each project's `.minit/` directory; the project remains the source of truth.

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

Adapters exist for macOS LaunchAgent, Linux systemd user services, and Windows Task Scheduler. Cross-platform unit/package CI passes on macOS, Windows, and Linux, but real-device login/reboot behavior and OS key-store availability in actual user sessions still require dogfooding before release claims are strengthened.

## Cloud administration without cloud ownership

The cloud layer exists to remove tedious administration without becoming the app runtime.

First inspect exactly what is eligible to leave the device in cleartext:

```bash
minit cloud preview
```

Eligible metadata is deliberately narrow: opaque app/device IDs, health/status, restart/autostart state, CPU/RAM/process metrics, aggregate run/live-time statistics, and encrypted-backup status.

Not eligible in cleartext: app names, source code, commands, paths, filenames, application data, raw logs, prompts, user inputs/outputs, secrets, or decryption keys.

A development cloud admin service exists under `cloud_service/`. It can be deployed to Railway or another container platform. It stores only allowlisted status metadata and already-encrypted `.mnb` backup objects.

Connect a local app:

```bash
minit cloud configure --url https://<admin-service>
```

The admin token is entered via a hidden prompt and stored in the approved local OS key store, not in the project file.

Manual operations remain available:

```bash
minit cloud sync
minit cloud backup <backup-id>
```

The cloud server can store/return ciphertext but does not possess the per-app key, backup data key, device root key, or user recovery key.

## Isolated cloud administration agent

Periodic cloud administration is deliberately separated from the application supervisor:

```bash
minit cloud agent start
minit cloud agent status
minit cloud agent stop
```

Default behavior:

- privacy-safe status sync every 60 seconds
- automatic backup **disabled**
- cloud/network/key-store errors are recorded in local cloud-agent state/logs
- retry uses bounded exponential backoff
- the local application supervisor is not stopped or restarted because status sync failed

Automatic encrypted backups require explicit opt-in because the first consistency model briefly stops the managed application:

```bash
minit cloud agent start --backup-every-hours 24
```

This creates a local authenticated `.mnb` backup first and uploads only that ciphertext.

The cloud agent itself still needs user-level autostart and real-device OS key-store validation before it should be considered production persistent.

See `docs/CLOUD_ADMIN_PRIVACY.md` and `cloud_service/README.md`.

## Validation to date

The local-manager development branch has been tested through repository CI on Ubuntu, Windows, and macOS, plus wheel build/install smoke testing.

Live dogfooding on clean hosted Linux machines has exercised multiple applications through `minit deploy`, local HTTP health, concurrent `minit run`, and external GET/POST requests. That exercise found a concurrent first-run `cloudflared` installation race; the installer is now serialized across local Minit processes and a regression test covers the behavior.

This CI and hosted dogfood are useful but are not substitutes for actual desktop login/reboot/key-store behavior. A real Windows/macOS/desktop-Linux dogfood period is the next reliability milestone.

## Current focus

Near-term development is focused on making the local runtime private, simple, and reliable:

1. real-device multi-app dogfood: installation, terminal close, login/reboot, crash/restart, key-store and autostart behavior
2. sandbox / filesystem and network boundaries
3. backup retention/freshness and additional explicit data paths
4. privacy-safe fleet/admin views and alerts
5. authenticated end-to-end remote administration where the server cannot fabricate privileged commands

Marketplace, discovery, monetization, and Remix are intentionally on hold while this foundation is built.
