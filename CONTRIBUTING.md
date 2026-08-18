# Contributing to Minit

Minit is early. The most useful contributions are small fixes, real-world tests, and concrete reports from apps that already work on localhost.

## Development setup

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
python -m venv .venv
```

Activate the virtual environment, then install Minit with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Run the tests

```bash
pytest -q
```

Keep changes focused and add or update tests when behavior changes.

## Test against a real app

Run any local HTTP app and publish it with:

```bash
minit run --port <port>
```

Useful test cases include Streamlit, FastAPI, Flask, Gradio, Vite/React, Next.js, and other AI-built local web apps.

The most valuable report answers:

- Did installation work without help?
- Did Minit find or accept the correct port?
- Did the public URL become reachable?
- Could a different device or network open it?
- Was any output confusing?

## Issues

Please use the structured GitHub issue templates for bugs and product feedback.

For a bug, include the smallest reproducible example you can provide:

- OS and CPU architecture
- Python version
- install method
- local app/framework and port
- command you ran
- expected behavior
- actual behavior

## Security

Do not post API keys, tokens, private URLs, personal data, company data, or other sensitive information in issues, logs, screenshots, or pull requests.

For security-sensitive vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Pull requests

Small and focused pull requests are preferred.

A good PR should:

1. explain the user-visible problem
2. make the smallest practical change
3. include tests when behavior changes
4. avoid adding dependencies unless they clearly reduce overall complexity
5. preserve the simple mental model: local app → `minit run` → another person can try it

Thank you for helping make Minit boringly reliable.
