# Changelog

All notable changes to Minit are documented here.

## 0.1.0 — 2026-08-18

First public alpha focused on one workflow:

```text
local app → minit run → public URL → real user
```

### Added

- `minit run` for publishing an already-running local web app
- automatic common-port detection
- temporary public URLs through Cloudflare Quick Tunnels
- automatic cross-platform networking helper setup
- pinned and SHA256-verified helper downloads
- public URL readiness retry before declaring a link live
- persistent local app identity in `.minit/app.json`
- `minit init`, `minit info`, and `minit doctor`
- Linux, macOS, and Windows CI
- package build/install smoke testing
- security policy and architecture documentation
- GitHub Pages project site

### Scope

Minit 0.1.0 is intended for prototypes, demos, and early user testing. Generated URLs should be treated as public. It is not intended for sensitive or production workloads.
