# Minit Commercialization Plan

## North star

Minit should make the transition from an AI-built local app to a real service feel continuous.

```text
Build → minit run → share → learn → minit deploy
```

The user should never feel that they are leaving Minit and starting a new infrastructure project.

## Product principles

1. **OSS must remain useful on its own.** `minit run` must not require signup or payment.
2. **Charge only after value appears.** The paid trigger is real usage creating an uptime/operations need.
3. **Same app, new runtime.** Local and managed modes share a persistent app identity.
4. **Do not sell cloud vocabulary.** Say “Keep this app online” rather than “Upgrade infrastructure.”
5. **Minimize irreversible architecture.** Keep the managed compute provider replaceable behind a Minit API.
6. **Security becomes stricter at each stage.** A public prototype and a persistent managed app must not share the same default security assumptions.

## Product ladder

### A. Minit OSS

Command:

```bash
minit run
```

Job to be done:

> Let another person try the app I just built.

Default characteristics:

- local compute
- temporary public URL
- no account
- no payment
- PC and terminal stay on
- intended for prototypes and early user tests

### B. Minit Managed

Command:

```bash
minit deploy
```

Job to be done:

> Keep this app online without my PC.

Initial managed scope:

- Minit account created only when deploying
- same persistent app ID
- source/build artifact upload
- managed build
- always-on runtime
- stable URL
- health check and restart
- runtime logs
- secrets/configuration

Second-wave scope:

- authentication / invite links
- custom domains
- usage analytics
- rollback
- resource sizing

### C. Team / Enterprise

Only after individual managed usage is healthy:

- teams and organizations
- ownership transfer
- SSO/OIDC
- private networking
- policy and audit
- centralized inventory
- spend controls

## Architecture boundary

Keep the public OSS repository focused on the local developer experience.

```text
Public OSS repo
  CLI
  local app identity
  local runtime
  publish/tunnel adapters
  deploy client protocol
          │
          ▼
Minit service API
  authentication
  app registry
  build orchestration
  runtime orchestration
  secrets metadata
  logs metadata
  billing
          │
          ▼
Replaceable infrastructure providers
  build
  compute
  storage
  networking
  observability
```

The CLI should depend on the Minit service contract, not directly on a specific managed compute vendor.

## App identity

`.minit/app.json` is the continuity anchor.

Minimum durable fields:

```json
{
  "schema_version": 1,
  "id": "persistent-uuid",
  "name": "my-app",
  "runtime": "local",
  "provider": "auto"
}
```

When managed deployment is introduced, do not replace the local ID. Link the existing ID to a server-side app record.

Potential future local fields should be added cautiously and remain backward compatible.

## `minit deploy` UX target

The target interaction is deliberately short:

```text
$ minit deploy

✓ App: customer-demo
✓ Local app identity found
→ Sign in to keep this app online
✓ Account connected
→ Preparing app
→ Building
→ Starting managed runtime

✓ Live: https://customer-demo.<managed-domain>
✓ Runtime: managed
✓ Status: always on
```

The first deploy may require account creation. `minit run` should not.

## Packaging strategy for managed beta

Do not attempt universal build detection on day one.

Recommended sequence:

1. Support a narrow, explicit set of common AI-built web app patterns.
2. Detect framework/runtime where confidence is high.
3. Show the detected build/run plan before uploading.
4. Fall back cleanly when unsupported rather than guessing.
5. Add Dockerfile support as an escape hatch for advanced users.

The initial framework list should be selected from actual Minit user projects rather than assumptions.

## Security model

### Local publishing

- generated URL is public by default
- warn against secrets/private data
- no implicit authentication
- temporary runtime

### Managed deployment

Before paid beta, require:

- encrypted transport
- encrypted secrets at rest
- isolated application runtimes
- explicit environment-variable handling
- build/runtime log separation
- resource limits
- abuse controls
- deletion workflow
- documented data retention
- dependency/build provenance

Authentication and secrets should be first-class managed features, not afterthoughts.

## Commercial model

Do not optimize pricing before the managed job is validated.

Initial principle:

> Free to launch. Pay to keep it alive.

A managed beta should use a simple plan with understandable limits rather than a complex cloud-style calculator. Usage-based components can be introduced once real workload distribution is known.

Questions to validate before final pricing:

- How long do managed apps stay alive?
- How much CPU/RAM do typical AI-built prototypes consume?
- How many apps does one builder keep active?
- Is stable uptime or auth the strongest willingness-to-pay trigger?
- Are users comfortable paying per app, per runtime, or for a bundle?

## Metrics

### OSS activation

1. install success
2. local app detected
3. public URL generated
4. external user successfully opens URL

### Product value

5. second Minit session
6. second project
7. public URL shared with multiple users

### Managed intent

8. requests for persistent URL
9. requests for auth
10. requests to run while PC is off
11. requests for logs/custom domain

### Commercial

12. deploy started
13. deploy succeeded
14. app still active after 7/30 days
15. paid conversion
16. managed retention

## Roadmap and gates

### Phase 0 — legal/product foundation

- [x] Commit an actual Apache-2.0 LICENSE file
- [x] Define OSS vs managed boundary
- [x] Define the `minit run → minit deploy` lifecycle
- [ ] Complete trademark/name clearance before meaningful commercial investment

### Phase 1 — make OSS reliable

- [x] Add CI workflow for Linux, macOS, and Windows
- [x] Pin and SHA256-verify the downloaded networking helper
- [x] Retry public URL readiness before declaring the link live
- [ ] packaging that does not require cloning the repository
- [ ] collect structured user feedback without mandatory telemetry

**Gate:** independent users repeatedly succeed with `minit run`.

### Phase 2 — managed-ready local architecture

- [x] version the local app manifest
- [x] preserve backward compatibility for existing manifests
- [ ] define deploy client/server protocol
- [ ] project/framework detection
- [ ] reproducible deployment bundle specification
- [ ] local `deploy --dry-run` inspection before upload

**Gate:** repeated user requests for always-on operation.

### Phase 3 — private managed alpha

- [ ] auth/control plane
- [ ] app registry keyed by persistent Minit app ID
- [ ] build service
- [ ] managed runtime adapter
- [ ] stable URL
- [ ] logs and health checks
- [ ] basic secrets

**Gate:** several users keep apps running because the managed service solves a real need.

### Phase 4 — paid beta

- [ ] simple billing
- [ ] quotas and resource controls
- [ ] support/delete/retention policies
- [ ] authentication/invite links
- [ ] custom domain
- [ ] operational dashboards

**Gate:** users voluntarily pay to keep apps online.

### Phase 5 — scale

- [ ] provider portability
- [ ] regional deployment
- [ ] improved isolation
- [ ] analytics/rollback
- [ ] team primitives

### Phase 6 — enterprise, only if demanded

- [ ] SSO/OIDC
- [ ] private network connectivity
- [ ] audit
- [ ] policy
- [ ] ownership/offboarding

## What not to build yet

- enterprise administration
- complex billing
- multi-region orchestration
- proprietary tunnel protocol
- elaborate analytics
- generalized Kubernetes abstraction

The current priority remains simple:

> **Get people who are not the author to successfully use Minit, then build the paid product around the pain that appears after they succeed.**
