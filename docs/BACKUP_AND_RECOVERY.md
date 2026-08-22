# Backup, Versioning, and Recovery Design

Minit's backup design must preserve the same local-first trust boundary as runtime management:

> **Remote storage may hold ciphertext. It must not hold the key that decrypts it.**

This document describes the intended design. Remote backup and disaster recovery are not yet implemented product guarantees.

## Separate three different jobs

Minit should not treat versioning, rollback, and disaster backup as one operation.

### 1. Code/config snapshot

Purpose: recover from a bad AI edit or configuration change quickly.

A code snapshot should capture the application's immutable/reproducible portion and support a fast rollback followed by a health check.

### 2. Mutable application data backup

Purpose: protect SQLite databases, uploaded files, indexes, user state, and other mutable data.

Data backup has different retention and restore semantics from code rollback. Rolling code back must not silently roll user data back unless explicitly requested.

### 3. Disaster recovery

Purpose: recover after the original machine is lost or its OS key store is unavailable.

This requires recovery material that exists outside the lost device while still remaining unavailable to Minit-operated servers.

## Code and data must be explicit before destructive rollback

Minit cannot safely infer that every file in a project directory is code.

Examples of mutable data that may live beside source code:

- `app.db`
- SQLite / DuckDB files
- uploaded files
- generated vector indexes
- user-created documents
- caches that are expensive or impossible to reproduce

Therefore automatic rollback must not simply replace the whole project directory.

The intended direction is:

```text
project / immutable app files
        │
        ├── code/config snapshot lifecycle
        │
        └── .minit/data/
             └── managed mutable data lifecycle
```

Minit already exposes `MINIT_DATA_DIR` to managed apps. Future app configuration may declare additional data paths for existing applications that cannot migrate their state immediately.

Auto-detection may suggest likely data paths, but destructive operations should require an explicit boundary.

## Key hierarchy

The intended local hierarchy is:

```text
OS-backed device root key
       │
       └── wraps per-app key
                 │
                 ├── local encrypted secrets
                 ├── backup data keys
                 └── protected app metadata
```

The device root key remains in the operating-system key store. The per-app key may exist on disk only in wrapped/encrypted form.

## Recovery paradox

If Minit-operated servers do not possess customer decryption keys, they also cannot magically restore encrypted data after every user-held key is lost.

That is a feature of the threat model, not an implementation bug.

A dependable remote backup therefore needs a second recovery path that does **not** create a Minit-held master key.

Candidate recovery paths:

1. **User-held recovery key** — generated locally and stored by the user in a password manager/offline location.
2. **Trusted second device** — the app key is wrapped to another user-controlled device.
3. **Organization-controlled recovery** — explicit customer-controlled escrow or threshold recovery for enterprise deployments.

Minit-operated infrastructure must never silently become the universal recovery holder.

## Recovery envelope direction

A future recovery setup can conceptually create:

```text
per-app key
    │
    ├── wrapped by device root key        → local app-key file
    │
    └── wrapped by user recovery key      → recovery envelope
```

The recovery envelope can be stored beside encrypted backups because it is not useful without the recovery key.

The recovery key itself must never be uploaded to Minit backup infrastructure.

## Remote-ready backup format

The backup payload should use a maintained streaming authenticated-encryption construction suitable for large files.

Minit should **not** implement a naive whole-file AES-GCM operation that requires loading a multi-gigabyte archive into memory, and should not invent an unaudited chunk protocol merely for convenience.

A future encrypted backup object should provide:

- confidentiality
- authenticated integrity
- streaming creation and restore
- format/version identifiers
- unique key/nonce material per backup as required by the selected primitive
- an app-bound context
- recovery metadata that does not reveal the recovery key

Only ciphertext is eligible for upload.

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

Cryptography can protect confidentiality and authenticated integrity, but it cannot guarantee availability. Freshness/rollback attacks also need explicit design; a signed backup can prove who created it but a compromised sole storage provider can still hide a newer backup.

Multiple user-controlled copies may therefore remain useful even with strong encryption.

## Rollback safety sequence

A future code rollback should be conservative:

```text
create pre-rollback snapshot
        ↓
stop local service
        ↓
restore code/config only
        ↓
keep mutable data unchanged by default
        ↓
start app
        ↓
health check
        ↓
commit rollback or automatically restore pre-rollback snapshot
```

Data restore should remain an explicit separate operation.

## Current implementation status

Already present on development `main`:

- persistent local app identity
- explicit `.minit/data` location exposed as `MINIT_DATA_DIR`
- OS-key-store direction for the device root key
- per-app key wrapped locally
- authenticated encrypted local secrets
- no Minit server key path

Still required before remote backup can be called dependable:

- user/organization recovery flow
- reviewed streaming encrypted backup format
- code/data path declaration
- backup manifests and retention
- restore validation
- optional multiple destinations
