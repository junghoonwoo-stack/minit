# Minit Cloud Admin Service (development)

This service is intentionally **not** an application hosting runtime.

Its role is limited to:

- receiving privacy-allowlisted operational status metadata
- storing and returning already-encrypted `.mnb` backup blobs

It is designed so a compromise of this service is not sufficient to decrypt application data or control a local Minit runtime.

## Railway deployment

A simple development deployment can use Railway with this repository and the `cloud_service/Dockerfile`.

Required environment variable:

```text
MINIT_ADMIN_TOKEN=<long random token>
```

Recommended persistent storage:

```text
MINIT_CLOUD_DATA_DIR=/data
```

Attach a Railway persistent volume at `/data` if backup/status persistence across deploys is required.

Optional backup size limit, in bytes:

```text
MINIT_MAX_BACKUP_BYTES=5368709120
```

Railway supplies `PORT`; the Dockerfile starts Uvicorn on that port.

## API surface

```text
GET  /health
POST /v1/status
GET  /v1/status
PUT  /v1/backups/{app_id}/{backup_id}
GET  /v1/backups/{app_id}
GET  /v1/backups/{app_id}/{backup_id}
```

All `/v1/*` endpoints require:

```text
Authorization: Bearer <MINIT_ADMIN_TOKEN>
```

The status schema rejects extra fields. The server is not intended to accept app names, source code, commands, paths, filenames, raw logs, prompts, inputs/outputs, secrets, or keys.

Backup upload accepts only the Minit encrypted `.mnb` container and checks that its cleartext format/app/backup identifiers match the requested object path. The server does **not** possess the key needed to authenticate/decrypt the encrypted payload itself.

## Local client

On a machine with development Minit installed:

```bash
minit cloud configure --url https://<your-service>.up.railway.app
minit cloud preview
minit cloud sync
minit cloud backup <backup-id>
```

The cloud token is entered through a hidden prompt and stored in the local OS key store. It is not written into the app project configuration.

Automatic periodic telemetry is deliberately not enabled yet. Explicit sync comes first so the privacy boundary is easy to inspect and test.

## Security boundary

Server compromise can still cause denial of service, deletion/withholding of backups, status forgery, or exposure of the explicitly retained operational metadata.

It must not grant plaintext access to the encrypted backup data. Future remote control commands will require end-to-end authorization verified by the local manager; the bearer token used by this development service must never become sufficient authority to execute local commands.
