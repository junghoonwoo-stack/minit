# Minit Architecture

Minit is intentionally small. The current job is to take an HTTP app already running on localhost and make it temporarily reachable from another device.

## Current request path

```text
remote user
    │
    ▼
public HTTPS URL
    │
    ▼
Cloudflare Quick Tunnel
    │
    ▼
Minit on your computer
    │
    ▼
127.0.0.1:<your-port>
    │
    ▼
your web app
```

Your application process and compute stay on your computer.

Minit does not currently run a hosted control plane, application server, account system, or database for this flow.

## What `minit run` does

1. Uses the port you provide, or checks a small set of common local development ports.
2. Confirms that something is listening on `127.0.0.1:<port>`.
3. Sends a local HTTP request as a basic health check.
4. Creates a persistent local Minit app identity in `.minit/app.json` if one does not already exist.
5. Finds a compatible `cloudflared` binary or downloads a pinned version.
6. Verifies downloaded helper binaries against an expected SHA256 digest before execution.
7. Starts a Cloudflare Quick Tunnel pointing at the local app.
8. Waits briefly for the generated public URL to become reachable before declaring it ready.
9. Keeps the tunnel alive until the Minit process is stopped.

## Why Cloudflare Quick Tunnel?

The current MVP uses Cloudflare Quick Tunnel because it provides a useful property for the first Minit workflow: a temporary HTTPS endpoint without asking the user to create an account or configure DNS.

Cloudflare is the current networking transport, not the architectural identity of Minit. The transport layer should remain replaceable.

## Local app identity

Each project can have a small local manifest:

```json
{
  "schema_version": 1,
  "id": "persistent-uuid",
  "name": "my-app",
  "runtime": "local",
  "provider": "auto"
}
```

The ID exists so Minit can recognize the same project across runs without coupling the project to a particular tunnel URL.

## What Minit does not do today

Minit does not currently:

- add authentication to your application
- inspect whether your application is safe to expose
- provide production hosting or uptime guarantees
- keep the app alive when your computer is off
- make a temporary URL private

See [SECURITY.md](../SECURITY.md) before publishing apps that contain anything sensitive.

## Design preference

Minit should keep infrastructure details behind a small interface and preserve a simple user model:

```text
my app already works locally
        ↓
     minit run
        ↓
 someone else can try it
```

If an infrastructure choice becomes visible to every user, it should be because the user needs to know about it — not because Minit leaked an implementation detail.
