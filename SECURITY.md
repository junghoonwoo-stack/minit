# Security Policy

Minit publishes a locally running web app to the public internet. That changes the security boundary of the app, so the default assumption should be simple:

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

## Networking helper

Minit may download a pinned networking helper on first use. Downloaded binaries are verified against an expected SHA256 digest before execution.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a security-sensitive vulnerability.

Use GitHub private vulnerability reporting when available for this repository. If that option is unavailable, contact the maintainer privately through the GitHub profile and include enough information to reproduce the issue.

For ordinary bugs that do not expose security-sensitive information, use GitHub Issues.
