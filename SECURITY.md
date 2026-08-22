# Security Policy

Minit is local-first. The application process and compute stay on a machine the user controls.

The current `minit run` command temporarily makes a locally running web app reachable from the public internet. That changes the app's security boundary, so the default assumption should be simple:

> **Treat every URL created by `minit run` as public.**

## Current scope

Minit is currently intended for prototypes, demos, and early user testing. It is not yet intended for sensitive or production workloads.

Before publishing an app:

- remove secrets, private files, personal data, and sensitive company data
- do not treat the generated URL as authentication
- add authentication inside the app if access control is required
- review AI-generated code for hard-coded API keys, debug endpoints, unsafe file access, or overly broad network access
- confirm the app exposes only the HTTP interface you intend to share

Stopping Minit closes the temporary public path, but it does not fix vulnerabilities in the application itself.

## Local state

Minit keeps project identity, runtime state, service configuration, logs, and future management metadata under the local `.minit/` directory.

The repository `.gitignore` excludes `.minit/` by default so machine-local operational state is not accidentally committed.

Service specifications must not contain plaintext secret values. Future secret storage will use a separate protected local mechanism.

## Server-compromise design goal

Future Minit coordination, relay, and backup services are being designed under a stronger assumption: **Minit-operated servers may be compromised.**

The intended architecture keeps application code, application data, plaintext secrets, and decryption keys on user-controlled machines. Any protected backup or sensitive remote-management payload that leaves the machine must be encrypted before upload or relay.

A compromised server may still disrupt availability or expose limited routing metadata. It should not be sufficient to decrypt protected application payloads or authorize privileged local actions.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the design invariants and limitations. These are target properties and must not be represented as completed guarantees until the corresponding mechanisms are implemented and reviewed.

## Networking helper

Minit may download a pinned networking helper on first use. Downloaded binaries are verified against an expected SHA256 digest before execution.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a security-sensitive vulnerability.

Use GitHub private vulnerability reporting when available for this repository. If that option is unavailable, contact the maintainer privately through the GitHub profile and include enough information to reproduce the issue.

For ordinary bugs that do not expose security-sensitive information, use GitHub Issues.
