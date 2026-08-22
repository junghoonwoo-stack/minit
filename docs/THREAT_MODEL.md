# Minit Threat Model

Minit is designed around a local-first trust boundary:

> **Your machine runs it. Your machine holds the keys. Minit coordinates without needing plaintext.**

This document defines the security properties Minit should preserve as local management, remote coordination, sharing, and encrypted backup are added.

## Security invariants

The following are design requirements, not optional implementation details:

1. Application code is authoritative on a user-controlled machine.
2. Application data is authoritative on a user-controlled machine by default.
3. Application secrets are not uploaded in plaintext to Minit services.
4. Decryption keys are generated and retained locally; Minit-operated servers must not possess them.
5. Any backup leaving the machine is encrypted before upload.
6. Any sensitive remote-management payload leaving an authorized client is encrypted before it reaches a Minit relay or storage service.
7. Remote commands are accepted only after local cryptographic verification and local policy checks.
8. A compromised Minit server must not be sufficient to decrypt customer application data, secrets, logs, or backups.
9. Minit must not claim a stronger property than it implements and has tested.

## Primary threat: Minit server compromise

Assume an attacker obtains administrative control of future Minit-operated infrastructure, including:

- routing / rendezvous services
- relay services
- metadata databases
- encrypted backup object storage
- deployment and operations dashboards

The attacker may be able to read, modify, delete, replay, delay, or block anything held by those services.

The intended result is:

### Confidentiality

The attacker cannot recover plaintext application code, application data, secrets, protected logs, encrypted backup contents, or local root/app keys from Minit infrastructure alone.

### Authorization

Possession of Minit server credentials alone must not allow the attacker to manufacture a locally accepted privileged command. Sensitive remote commands must be signed/authenticated by an authorized user/device and verified locally.

### Integrity

Encrypted objects and commands must be authenticated, not merely encrypted. Modification of ciphertext must be detected before use.

### Availability

A compromised server can still disrupt availability: it may delete encrypted backups, refuse routing, or withhold messages. Cryptography cannot prevent this.

Minit should therefore support independent local copies and eventually user-controlled secondary backup destinations where appropriate.

## Metadata Minit may still observe

A coordination service may need some metadata to function, for example:

- opaque user/device/app identifiers
- whether a device is online
- approximate connection timing
- routing source/destination identifiers
- ciphertext sizes
- service health needed for routing

Minit should minimize retained metadata and must distinguish metadata privacy from payload confidentiality.

The target claim is:

> **Minit services cannot read protected application payloads.**

Not:

> Minit services learn literally nothing.

## Local-machine compromise

If the machine running an application is fully compromised while keys or plaintext are in use, an attacker may access decrypted data, process memory, credentials available to the application, or the local key store.

This is outside the protection that end-to-end encryption against server compromise can provide.

Minit should still reduce blast radius with sandboxing, least privilege, per-app keys, filesystem boundaries, and resource/network policies.

## Key hierarchy direction

The target hierarchy is envelope encryption rather than one global key used directly for everything.

```text
Device / user root protection
        │
        ├── App key A
        │     ├── backup data key 1
        │     ├── backup data key 2
        │     └── protected app state
        │
        └── App key B
              └── ...
```

Principles:

- use cryptographically secure random keys
- use established authenticated-encryption primitives through maintained libraries
- use a fresh nonce and/or data key according to the selected primitive's requirements
- keep root/key-encryption material in OS-backed secure storage where practical
- separate keys between applications so compromise of one app key does not automatically expose every app
- support key rotation without requiring plaintext to be available to a server

Minit should not implement novel cryptographic primitives.

## Remote commands

A future remote command such as `restart`, `backup`, or `share` should conceptually follow this path:

```text
authorized admin device
        │
        ├─ construct command + command id + freshness data
        ├─ authenticate/sign
        └─ encrypt for target device
                │
                ▼
        Minit relay/mailbox
        (ciphertext only)
                │
                ▼
        target Local Manager
        ├─ decrypt
        ├─ verify sender
        ├─ reject replay/expired command
        ├─ enforce local policy
        └─ execute
```

The relay must not be the final authorization authority.

## Encrypted backup

A backup that leaves the machine should follow:

```text
local files/data
      ↓
snapshot locally
      ↓
compress locally
      ↓
encrypt + authenticate locally
      ↓
ciphertext object
      ↓
remote storage
```

Restore reverses the process only after the ciphertext is back on an authorized machine.

Remote storage should never receive the plaintext data-encryption key.

## Recovery is intentionally hard

If Minit cannot decrypt user data, Minit also cannot magically recover data when every authorized copy of the key is lost.

A recovery design is therefore required before encrypted remote backup is presented as dependable. Likely options include:

- a user-held recovery key stored offline
- recovery material on another trusted user-owned device
- for organizations, explicit customer-controlled recovery/escrow policies

Minit-operated infrastructure must not silently retain a universal recovery secret, because that would defeat the server-compromise threat model.

## Sharing

Future sharing should grant cryptographic access rather than upload a reusable plaintext app key to Minit.

Conceptually, an app key can be wrapped/encrypted to an authorized recipient/device public key. Removing a recipient requires an explicit revocation/key-rotation policy; deleting an ACL row on a server is not by itself cryptographic revocation for keys a recipient already possesses.

## Security before convenience

Features should remain local-only until the remote path can preserve these invariants.

Examples:

- persistent local process management can ship before remote management
- local snapshots can ship before remote encrypted backup
- temporary public sharing can remain explicitly public until Minit has real access control
- a permanent public endpoint should not be introduced merely for convenience before authentication and authorization are sound

## Non-goals for early releases

Early Minit releases do not yet claim:

- audited zero-knowledge security
- sandbox isolation against malicious applications
- secure multi-user key distribution
- secure remote administration
- encrypted remote backup
- protection if the local host is fully compromised

Those claims should be introduced only as the corresponding mechanisms are implemented and reviewed.
