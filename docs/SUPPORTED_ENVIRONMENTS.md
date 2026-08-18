# Supported environments

Minit is currently tested and intended for lightweight prototype sharing from a developer machine.

## Python

- Python 3.11+
- Package: `minit-runtime`
- CLI command: `minit`

## Operating systems

Automatic networking setup currently supports:

- macOS — Apple Silicon (arm64)
- macOS — Intel (amd64)
- Windows — x64
- Linux — x64
- Linux — arm64

## Local apps

Minit works with an already-running local HTTP application reachable at `127.0.0.1:<port>`.

Common ports auto-checked by the current MVP include:

- 3000
- 5173
- 8000
- 8080
- 8501
- 8888

If your app uses another port, specify it explicitly:

```bash
minit run --port 7860
```

## Current transport

The current MVP uses Cloudflare Quick Tunnels for the temporary public path. Minit downloads a pinned helper release when needed and verifies its SHA256 before running it.

## Intended use

Current scope:

- prototypes
- demos
- early user testing
- short-lived sharing

Not current scope:

- sensitive data
- production workloads
- guaranteed uptime
- stable URLs
- built-in authentication
- custom domains

See [SECURITY.md](../SECURITY.md) before exposing a local app to the public internet.
