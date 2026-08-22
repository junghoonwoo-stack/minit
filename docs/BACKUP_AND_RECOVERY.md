# Backup, Versioning, and Recovery Design

Minit's backup design preserves the same local-first trust boundary as runtime management:

> **Remote storage may hold ciphertext. It must not hold the key that decrypts it.**

## Separate three different jobs

Minit does not treat versioning, rollback, and disaster backup as one operation.

### 1. Code/config snapshot

Purpose: recover from a bad AI edit or configuration change quickly.

Development `main` already provides source/config snapshots and conservative rollback. `.minit/data` is deliberately excluded.

### 2. Mutable application data backup

Purpose: protect SQLite databases, uploaded files, indexes, user state, and other mutable data.

Development `main` now provides a first encrypted backup lifecycle for `.minit/data`:

```bash
minit backup create
minit backup list
minit backup verify <backup-id>
minit backup restore <backup-id>
```

The first implementation intentionally uses `.minit/data` as the explicit managed mutable-data boundary rather than guessing which arbitrary project files are state.

### 3. Disaster recovery

Purpose: recover after the original machine is lost or its OS key store is unavailable.

Minit supports a user-held recovery-key envelope for the per-app key. The recovery key itself is not stored by Minit.

## Code and data are explicit before destructive rollback

Minit cannot safely infer that every file in a project directory is code.

Examples of mutable data that may live beside source code:

- `app.db`
- SQLite / DuckDB files
- uploaded files
- generated vector indexes
- user-created documents
- caches that are expensive or impossible to reproduce

Therefore automatic code rollback does not replace the whole project directory.

The current boundary is:

```text
project / source and config
        │
        ├── code/config snapshot lifecycle
        │
        └── .minit/data/
             └── encrypted mutable-data backup lifecycle
```

Minit exposes `MINIT_DATA_DIR` to managed apps. Future configuration may declare additional explicit data paths for existing applications that cannot migrate their state immediately.

## Key hierarchy

The local hierarchy is:

```text
OS-backed device root key
       │
       └── wraps per-app key
                 │
                 ├── local encrypted secrets
                 ├── wraps backup data keys
                 └── protected app metadata

user-held recovery key
       │
       └── separately wraps the per-app key
```

The device root key remains in the operating-system key store. The per-app key may exist on disk only in wrapped/encrypted form.

## User-held recovery

If Minit-operated servers do not possess customer decryption keys, they also cannot magically restore encrypted data after every user-held key is lost.

That is a feature of the threat model, not an implementation bug.

Current development flow:

```bash
minit recovery create
```

This generates a 256-bit recovery key locally, displays it once for the user to store elsewhere, and writes only a recovery envelope containing the app key encrypted under that recovery key.

On a replacement device, after the app/recovery metadata is available:

```bash
minit recovery restore
```

The recovery key is entered through a hidden prompt and the recovered per-app key is re-wrapped for the new device's OS-backed root key.

Minit-operated infrastructure must never silently become the universal recovery holder.

## Streaming encrypted data backup

The current `.mnb` format uses maintained primitives from `cryptography`:

- a fresh 256-bit backup data key per backup
- AES-256-GCM authenticated encryption for the backup stream
- a fresh random GCM nonce per backup
- the backup data key wrapped locally by the per-app key
- authenticated header metadata bound as GCM AAD
- streaming `tar+gzip` directly into the encryptor

The backup path does **not intentionally write a plaintext tar archive to disk**.

Conceptually:

```text
.minit/data
    ↓
stream tar + gzip
    ↓
AES-256-GCM on device
    ↓
.minit/backups/<opaque-id>.mnb
```

The encrypted object header contains only the information required to identify/decrypt the format locally, including opaque app/backup identifiers and wrapped key material. Filenames and file contents remain inside the encrypted tar stream.

## Consistency and service lifecycle

For reliability, `minit backup create` checks whether the Minit-managed app is running. If so, it stops the managed service before reading `.minit/data`, creates and verifies the authenticated backup, then restarts the service.

This intentionally favors simple consistency over zero-downtime backup in the first implementation.

It guarantees consistency only for data placed inside the managed `.minit/data` boundary. Applications that write mutable state elsewhere need an explicit future data-path declaration before Minit can claim to back that state up.

## Restore safety

Restore is intentionally conservative:

```text
verify entire encrypted backup
        ↓
stop managed app if running
        ↓
decrypt/extract into private staging directory
        ↓
only after successful extraction:
atomically replace .minit/data directory
        ↓
restart managed app if it was running
```

Unsafe archive member paths, symlinks, hard links, and device entries are rejected.

A tampered ciphertext or authentication tag fails integrity verification before current application data is replaced.

## Cloud-ready backup objects

Only the encrypted `.mnb` object is eligible for future blind cloud backup storage.

Cloud administration may retain minimal operational metadata such as:

- opaque backup ID
- creation timestamp
- ciphertext byte size

It does not need filenames, source paths, raw application data, app secrets, backup data keys, per-app keys, or recovery keys.

See [Cloud Administration Privacy Boundary](CLOUD_ADMIN_PRIVACY.md).

## Storage is replaceable

Once encrypted locally, the same backup object could be stored in:

- a user-selected external disk/NAS
- S3-compatible object storage
- a user-controlled cloud bucket
- future Minit blind backup storage

The storage provider should not alter the encryption trust model.

## Server compromise

If remote storage is compromised, the attacker may:

- delete backup ciphertext
- withhold it
- return an older valid backup
- observe object sizes/timing and other retained metadata

The attacker must not be able to decrypt the backup from server-side material alone.

Cryptography can protect confidentiality and authenticated integrity, but it cannot guarantee availability. Freshness/rollback attacks also still require explicit design; a compromised sole storage provider can hide a newer valid backup.

Multiple user-controlled copies may therefore remain useful even with strong encryption.

## Remaining work

Before encrypted cloud backup can be called production-ready, Minit still needs:

- real-device validation of OS-backed key stores
- recovery-key rotation and multi-device recovery UX
- explicit additional data-path declarations beyond `.minit/data`
- retention/scheduling policy
- cloud ciphertext upload/download transport
- backup freshness/rollback-attack handling
- Windows ACL hardening
- larger-scale performance and interruption testing
