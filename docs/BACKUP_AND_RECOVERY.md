# Backup, Versioning, and Recovery Design

Minit's backup design must preserve the same local-first trust boundary as runtime management:

> **Remote storage may hold ciphertext. It must not hold the key that decrypts it.**

Remote backup is not yet a product guarantee. Local source/config rollback and a user-held recovery-key foundation are now implemented on development `main`.

## Separate three different jobs

Minit should not treat versioning, rollback, and disaster backup as one operation.

### 1. Code/config snapshot

Purpose: recover from a bad AI edit or configuration change quickly.

The current development implementation captures a conservative set of source/config files, stores a local integrity manifest, creates a safety snapshot before rollback, and can restart a previously running service after restore.

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

The current direction is:

```text
project / immutable app files
        │
        ├── code/config snapshot lifecycle
        │
        └── .minit/data/
             └── managed mutable data lifecycle
```

Minit exposes `MINIT_DATA_DIR` to managed apps. The current snapshot implementation excludes `.minit/` entirely and therefore does not modify `.minit/data` during rollback. It also deliberately does not delete source files that were created after the target snapshot; exact/pruning rollback requires a stronger declared data boundary first.

Future app configuration may declare additional data paths for existing applications that cannot migrate their state immediately. Auto-detection may suggest likely data paths, but destructive operations should require an explicit boundary.

## Key hierarchy

The local hierarchy is:

```text
OS-backed device root key
       │
       └── wraps per-app key
                 │
                 ├── local encrypted secrets
                 ├── future backup data keys
                 └── protected app metadata
```

The device root key remains in an approved operating-system key store when available. Minit fails closed rather than using a plaintext key-file fallback. The per-app key may exist on disk only in wrapped/encrypted form.

## Recovery paradox

If Minit-operated servers do not possess customer decryption keys, they also cannot magically restore encrypted data after every user-held key is lost.

That is a feature of the threat model, not an implementation bug.

A dependable remote backup therefore needs a second recovery path that does **not** create a Minit-held master key.

Candidate recovery paths remain:

1. **User-held recovery key** — implemented as the first recovery path on development `main`.
2. **Trusted second device** — future app-key wrapping to another user-controlled device.
3. **Organization-controlled recovery** — future customer-controlled escrow or threshold recovery for enterprise deployments.

Minit-operated infrastructure must never silently become the universal recovery holder.

## User-held recovery envelope

Development `main` now supports:

```text
per-app key
    │
    ├── wrapped by device root key        → local app-key file
    │
    └── wrapped by user recovery key      → local recovery envelope
```

`minit recovery create` generates a random 256-bit recovery key locally and prints it once for the user to store outside the machine. The recovery key itself is not written to the recovery-envelope file and there is no server upload path for it.

`minit recovery restore` accepts the recovery key through a hidden prompt, unlocks the app key locally, and re-wraps that app key under the current device's OS-backed root key.

The current implementation intentionally refuses to silently rotate an existing recovery key. Recovery-key rotation, multi-device recovery, and organization-controlled recovery remain future work.

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

## Current rollback safety sequence

Development `main` now follows this conservative sequence for source/config rollback:

```text
create pre-rollback safety snapshot
        ↓
stop local service if running
        ↓
verify snapshot identity/path/hash integrity
        ↓
restore source/config files only
        ↓
keep mutable data unchanged
        ↓
restart app if it was running
        ↓
wait for health result
```

If restart fails after files are restored, Minit reports the safety-snapshot ID so the operator retains a known recovery point. Data restore remains an explicit separate future operation.

## Current implementation status

Already present on development `main`:

- persistent local app identity
- explicit `.minit/data` location exposed as `MINIT_DATA_DIR`
- conservative source/config snapshots independent of Git knowledge
- per-file SHA256 integrity manifest and path-safety checks
- safety snapshot before rollback
- source rollback that preserves mutable `.minit/data`
- service restart/health verification after rollback when applicable
- OS-backed device-root-key direction with fail-closed backend policy
- per-app key wrapped locally
- authenticated encrypted local secrets
- user-held recovery-key envelope and new-device app-key re-wrapping
- no Minit server key path

Still required before remote backup can be called dependable:

- reviewed streaming authenticated-encryption format
- crash-consistent database/data snapshot semantics
- backup manifests, retention, and freshness policy
- encrypted remote storage path
- restore validation for mutable data
- recovery-key rotation / trusted-device / organization-controlled recovery
- optional multiple backup destinations
