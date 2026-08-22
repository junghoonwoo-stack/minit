# Connectivity and Identity Direction

Minit's future remote-access path must preserve the same server-compromise boundary as local storage:

> **A Minit relay should route traffic without possessing the keys needed to read protected application traffic.**

This is a design direction, not a current `minit run` guarantee.

## Current temporary path

Today `minit run` uses Cloudflare Quick Tunnel for a fast prototype-sharing experience.

That is useful for the current public/prototype workflow, but it is **not** the target security architecture for permanent private applications. A conventional HTTPS reverse proxy/edge that terminates browser TLS is capable, in principle, of seeing application payloads at that termination point.

Minit must not present transport encryption to a relay as equivalent to end-to-end encryption from the remote client to the user's machine.

## Target path

Conceptually:

```text
browser / authorized client
          │
          │ end-to-end protected session
          ▼
     blind router / relay
          │
          │ opaque protected traffic
          ▼
   Minit Local Gateway
          │
          ▼
   127.0.0.1:<app-port>
```

The relay may need routing metadata, but it should not have the application-session decryption key.

## Prefer direct connectivity

The preferred order remains:

```text
direct connection when practical
          ↓
blind relay when direct connectivity is required
```

NAT, CGNAT, and corporate firewalls mean a relay will still be necessary for some users.

## Browser TLS is a real design constraint

A normal browser must trust the HTTPS certificate presented for the application hostname.

If Minit terminates TLS centrally for convenience, a compromised Minit server or edge can potentially observe plaintext. Therefore a strong zero-server-key design needs a way for the TLS/application decryption endpoint to remain on the user's side while preserving a browser-trusted experience.

Candidate directions require careful validation and may include:

- layer-4 TLS passthrough with SNI-based routing, where the leaf/private key stays on the local machine
- per-device/per-app browser-trusted certificates whose private keys are generated locally
- negotiated CA/ACME issuance approaches that scale without sharing a wildcard private key with Minit infrastructure
- an application-level E2E protocol only if the browser bootstrap itself can remain trustworthy under server compromise

A shared wildcard TLS private key on Minit infrastructure would create a universal decryption/impersonation key and is incompatible with the strongest threat model.

Certificate issuance/rate limits and browser compatibility must be solved before a permanent `*.minit.app` URL is claimed to be zero-server-knowledge.

## Identity must not become a backdoor authorization authority

Another subtle problem is authentication.

If a Minit server can mint an arbitrary bearer token saying "this is Alice", then compromise of that server could grant an attacker access even if network traffic is encrypted.

The local gateway must remain the final authorization authority.

Strong candidate models include:

- passkey/public-key credentials verified by the local gateway
- third-party OIDC identity tokens (for example an external identity provider) verified locally against the issuer's public keys
- owner/admin signed capability grants
- encrypted recipient key wrapping for shared app keys/capabilities

A Minit relay may help discover identities and deliver encrypted/signed grants, but should not be able to forge a locally accepted privileged identity by itself.

Email magic-link authentication operated solely by Minit would require additional design because a compromised email/token issuer could otherwise impersonate users.

## Remote administration

Administrative commands such as restart, backup, share, or configuration changes should be authenticated end-to-end:

```text
admin device
   │ signed + encrypted command
   ▼
blind mailbox/relay
   ▼
local manager
   ├─ verify authorized signer
   ├─ verify command id/freshness
   ├─ reject replay
   ├─ apply local policy
   └─ execute
```

Server possession of a database row such as `role=admin` must not, on its own, be sufficient to forge a command accepted by the local machine.

## Stable URLs should wait for this boundary

For that reason, current development separates:

- `minit deploy` → persistent local process management
- `minit run` → explicitly temporary/public sharing

Permanent private remote access should be added only when its connectivity and authorization design preserves the intended threat model.

## Metadata remains visible

Even a blind relay may observe some combination of:

- source/destination network addresses
- opaque device/app routing IDs
- connection timing and duration
- traffic volume
- TLS SNI/hostname unless an appropriate ECH design is in use

This should be minimized and documented rather than hidden behind an inaccurate "server learns nothing" claim.
