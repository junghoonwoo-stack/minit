# Cloud Administration Privacy Boundary

Minit's cloud administration layer is intentionally **not** the application runtime and must not become a second source of truth for customer software.

> **Local is authoritative. Cloud is observational and coordinative.**

The application code, mutable data, secrets, decryption keys, raw logs, prompts, inputs, outputs, and execution remain on user-controlled machines.

## What may leave the device in cleartext

Only a narrow operational allowlist is eligible for a future Minit administration service:

- opaque app ID
- opaque device ID
- observation timestamp
- configured/running/health status
- restart count
- autostart state
- CPU / resident memory / child-process count
- aggregate successful-run count and live duration
- latest encrypted-backup ID, creation time, and ciphertext size

The implementation lives in `minit/cloud_contract.py`. Adding a field to that schema should be treated as a privacy/security decision.

Use:

```bash
minit cloud preview
```

to inspect the complete cleartext payload currently eligible for transmission. No automatic telemetry transport is configured yet.

## What must not leave the device in cleartext

The cloud status/control API must not receive:

- app/project names
- source code
- commands or command arguments
- local filesystem paths or filenames
- mutable application data
- raw logs or stack traces
- prompt/conversation contents
- user inputs or model/app outputs
- secret names or secret values
- API tokens/passwords
- device root keys, per-app keys, recovery keys, backup data keys

If a future feature needs one of these values remotely, it requires either a redesign or end-to-end encryption where Minit-operated infrastructure still cannot decrypt it.

## Encrypted backups

Mutable data is backed up separately from source snapshots. The current development implementation backs up `.minit/data` using streaming authenticated encryption.

The encrypted `.mnb` backup object may eventually be uploaded to blind object storage. The storage service may learn the object size, timing, opaque identifiers, and other explicitly retained metadata, but must not receive the data-decryption key.

Backup creation follows this trust boundary:

```text
.minit/data
    ↓
stop managed app if running
    ↓
stream tar+gzip
    ↓
stream AES-256-GCM encryption on device
    ↓
.mnb ciphertext
    ↓
(optional future cloud storage)
```

No plaintext tar archive is intentionally written to disk by the backup path.

## Cloud management commands

Future remote administration (restart, stop, backup request, etc.) must not make the Minit server a privileged execution authority.

The intended direction is:

1. an authorized user/device creates a command locally,
2. the command is signed and/or end-to-end encrypted to the target device,
3. Minit infrastructure relays opaque command material,
4. the local manager verifies authorization, freshness, and replay protection,
5. only the local manager decides whether to execute the action.

Server database access alone must not be sufficient to fabricate a privileged local command.

## Server compromise expectation

A total compromise of Minit-operated cloud infrastructure may cause:

- monitoring outage
- relay outage
- backup deletion/withholding
- exposure of explicitly retained operational metadata

It must not by itself reveal customer app/data/secrets/backups in plaintext or provide the cryptographic authority needed to control a local runtime.

This is a design invariant. It should be tested at serialization and command-authentication boundaries, not merely stated as policy.
