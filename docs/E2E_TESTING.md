# Minit E2E testing notes

This document records what we learned from the first real end-to-end test of Minit.

## What was validated

The following full path worked on a GitHub-hosted Linux runner:

```text
start local web app
→ install Minit
→ minit run --port 8000
→ public URL created
→ external HTTPS request reached the local app
```

The test page returned successfully through the generated public URL, confirming that the MVP works end to end.

## Important observations

### 1. Public URL creation is not the same as immediate reachability

The URL may be printed before DNS and edge routing are fully ready. In the first live test, several requests failed briefly before the same URL became reachable.

Tests and future Minit clients should therefore retry external reachability for a short period instead of treating the first DNS/network failure as a hard failure.

### 2. ICMP warnings are not fatal for HTTP publishing

On the GitHub runner, the tunnel process logged warnings about ICMP proxy permissions. HTTP/HTTPS publishing still worked correctly.

Minit should avoid surfacing these warnings as fatal errors unless they affect the actual HTTP tunnel.

### 3. The URL lives with the Minit process

The current MVP URL is temporary. When the Minit/tunnel process stops, the URL stops working.

This matches the intended local-first MVP behavior: the user's PC and Minit process are the runtime.

### 4. External verification matters

A local health check is not enough. E2E testing should verify both:

1. the app responds on `127.0.0.1:<port>`;
2. the generated public URL returns the expected content from outside the local process.

## Recommended E2E test pattern

For automated tests:

1. Start a tiny local HTTP server.
2. Run `minit run --port <port>` in the background.
3. Capture the generated URL.
4. Retry the public URL for up to ~30–60 seconds.
5. Assert that the expected page content is returned.
6. Stop Minit and clean up the local server.

Keep these tests separate from normal unit tests because they depend on external networking.

## Current scope

This validates the current MVP transport and CLI flow. It does not yet validate stable URLs, authentication, custom domains, or long-running reliability.
