# Minit Deploy Protocol — Draft

This document defines the first boundary between the open-source CLI and a future Minit Managed service. It is intentionally a draft; no server implementation exists yet.

## Goal

`minit deploy` should promote the same app identity from local runtime to managed runtime.

```text
local app + .minit/app.json
          ↓
      minit deploy
          ↓
      Minit API
          ↓
 build + managed runtime
```

## Design rules

1. The persistent local app ID is never replaced during deployment.
2. The CLI talks to a Minit API, not directly to a compute vendor.
3. The user can inspect what will be uploaded before the first upload.
4. Secrets are not included in a source bundle by default.
5. Unsupported project types fail explicitly rather than being guessed into production.
6. The protocol should be versioned independently from the local manifest schema.

## Proposed flow

### 1. Inspect

```bash
minit deploy --dry-run
```

Produces a local deployment plan:

```text
App: customer-demo
App ID: <persistent UUID>
Detected runtime: python
Detected framework: streamlit
Build plan: <human-readable plan>
Files to upload: <count / size>
Excluded: .git, .minit secrets, virtualenvs, caches, known secret files
```

No account and no upload should be required for `--dry-run`.

### 2. Authenticate

The first real `minit deploy` opens a browser/device flow and connects a Minit account.

Authentication is a managed-service concern. `minit run` remains account-free.

### 3. Register/link app

Request conceptually contains:

```json
{
  "protocol_version": 1,
  "local_app_id": "persistent-uuid",
  "name": "customer-demo",
  "project_fingerprint": "..."
}
```

The service returns a server-side app record linked to the same local app ID.

### 4. Create deployment

The CLI sends metadata describing the reproducible build plan and an upload manifest.

The service returns a deployment ID and upload instructions.

### 5. Upload bundle

The bundle should be deterministic and inspectable.

Initial exclusion policy should include at least:

- `.git/`
- `.minit/` service credentials if introduced later
- virtual environments
- dependency caches
- OS/editor caches
- `.env` and known secret files by default

Secrets should be supplied through a separate explicit mechanism.

### 6. Build and run

The CLI follows deployment state:

```text
preparing → uploading → building → starting → healthy
```

Failures should surface the relevant build/runtime log without requiring knowledge of the underlying infrastructure vendor.

### 7. Link local state

Only after a successful managed deployment should local state record the managed linkage.

Possible future fields:

```json
{
  "runtime": "managed",
  "managed": {
    "app_ref": "server-side-reference",
    "url": "https://..."
  }
}
```

The exact field shape is not final. Backward compatibility is required.

## API sketch

Names are placeholders, not commitments.

```text
POST /v1/apps/link
POST /v1/apps/{app}/deployments
POST /v1/deployments/{deployment}/bundle
GET  /v1/deployments/{deployment}
GET  /v1/deployments/{deployment}/logs
```

## What is deliberately not decided yet

- managed compute vendor
- build system/vendor
- final framework support list
- billing model
- managed domain name
- exact auth provider
- source upload vs remote Git integration as the primary path

Those decisions should be made from real user projects and operational experiments, not from the CLI contract alone.
