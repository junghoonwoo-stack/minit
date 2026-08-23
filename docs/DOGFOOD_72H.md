# 72-hour real-device dogfood

This is the release-readiness exercise for Minit's local-manager development branch (`main / 0.2.0.dev0`).

The goal is not load testing. It is to find the desktop problems that hosted CI cannot reproduce reliably: OS key stores, login/reboot persistence, Task Scheduler / LaunchAgent / systemd-user behavior, real filesystem paths, sleep/wake, terminal closure, and normal multi-app use.

Use only test/demo apps and dummy secrets during this phase.

## 1. Install development `main`

Recommended before an alpha PyPI release:

```bash
pipx install --force "git+https://github.com/junghoonwoo-stack/minit.git@main"
minit --help
```

If `pipx` is not installed, install it using the normal Python tooling for the machine, reopen the shell if PATH changes, then rerun the command above.

Do not confuse this with the stable PyPI `0.1.0`; the local manager is still development software.

## 2. Check the real OS key store

```bash
minit security doctor
```

Expected: an approved OS-backed backend and `trusted: yes`.

If this fails, stop the secret/recovery portion of dogfood and record the backend/reason. Do not work around it with a plaintext/fallback keyring.

## 3. Create two harmless local apps

Use any two non-sensitive web projects, or create two static demo folders. Each folder only needs an `index.html`.

In app A:

```bash
minit deploy
minit open
```

In app B:

```bash
minit deploy
minit open
```

Minit should choose different localhost ports automatically when the preferred port is already used or reserved.

From any other directory:

```bash
minit ls
minit status <app-a-name>
minit status <app-b-name>
```

Run `minit deploy` again inside app A. Expected: `Already running`, not a port-conflict error.

## 4. Close the terminals

Close the shells used to deploy both apps. Open a fresh shell and run:

```bash
minit ls
minit open <app-a-name>
minit open <app-b-name>
```

Both apps should still be running.

## 5. Exercise the real key store with a dummy secret

Inside one demo project:

```bash
minit security init
minit secret set MINIT_DOGFOOD_TOKEN
minit secret list
```

Use a disposable dummy value. Never paste the value into an issue or test report.

Optionally create recovery material:

```bash
minit recovery create
```

The recovery key is user-held. Store it somewhere off the tested machine if you create it; never paste it into logs, GitHub, chat, or Minit cloud.

## 6. Enable autostart for one demo app

Inside app A:

```bash
minit autostart install
minit autostart status
```

Expected platform implementations:

- Windows: user Task Scheduler entry
- macOS: user LaunchAgent
- Linux desktop: systemd user service

Do not enable autostart for sensitive real applications during this test.

## 7. Reboot once

Reboot/login normally. Do not manually start app A first.

After login:

```bash
minit ls
minit status <app-a-name>
minit open <app-a-name>
```

App A should return through autostart. App B is expected to remain stopped after reboot unless autostart was also installed for it.

Also rerun:

```bash
minit security doctor
minit secret list
```

This checks whether the key-store context used after a real login/reboot still works.

## 8. Leave it running for 72 hours

During the period, normal sleep/wake and network changes are useful. Once or twice a day:

```bash
minit ls
minit status <app-a-name>
```

Check that:

- the supervisor is still alive
- the app is healthy/reachable locally
- CPU/RAM values look plausible
- repeated `minit deploy` remains idempotent
- local management works even if internet access is unavailable

Cloud sync or public `minit run` is not required for this local-runtime test.

## 9. Exercise local recovery paths with demo data

For source/config rollback, make a harmless source change around a snapshot:

```bash
minit snapshot create --label dogfood-before-change
minit snapshot list
```

Then use `minit rollback <snapshot-id>` only on the disposable demo project.

For mutable data backup, put disposable test data under the app's `MINIT_DATA_DIR` / `.minit/data`, then:

```bash
minit backup create
minit backup list
minit backup verify <backup-id>
```

A destructive restore test should be done only with disposable data.

## 10. Finish / cleanup

Inside the app with autostart:

```bash
minit autostart remove
```

From anywhere:

```bash
minit stop <app-a-name>
minit stop <app-b-name>
```

Keep the project `.minit/` folders until any failures have been understood. Do not publish raw logs if they contain application-specific content.

## What to report

The highest-value findings are behavioral, not screenshots:

- operating system and Python installation style
- whether GitHub-main installation was smooth
- whether `minit deploy` worked without extra flags
- whether two apps received distinct ports
- whether terminal closure changed anything
- whether autostart survived a real reboot/login
- whether the approved OS key store remained usable after reboot
- whether sleep/wake caused app/supervisor problems
- any confusing CLI moment

Never include secret values or recovery keys in a report.

## Release gate

Do not mark real-device persistence ready solely from CI. Phase 1 is considered release-ready only after representative Windows/macOS/desktop-Linux login/reboot/key-store behavior has been exercised on actual desktops and remaining platform-specific issues are resolved.
