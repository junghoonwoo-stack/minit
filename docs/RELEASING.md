# Releasing Minit

Minit releases are intentionally boring and reproducible.

## Before a release

1. Confirm the version in `pyproject.toml`.
2. Update `CHANGELOG.md` and replace `unreleased` with the release date.
3. Confirm CI passes on Linux, macOS, and Windows.
4. Confirm the package job can build a wheel, install it into a fresh environment, and run `minit --help`.
5. Run one live smoke test separately from normal CI:
   - start a tiny local app
   - run `minit run --port <port>`
   - open the generated URL from another network/device
   - confirm the expected page content is returned
6. Review `SECURITY.md` and make sure release notes do not overstate the current security or production scope.

## PyPI publishing

Publishing uses GitHub Actions and PyPI Trusted Publishing. No long-lived PyPI API token should be stored in GitHub.

The publisher configuration on PyPI must match:

- GitHub owner: `junghoonwoo-stack`
- repository: `minit`
- workflow: `release.yml`
- environment: `pypi`
- PyPI project: `minit-runtime`

The first release can use a PyPI pending Trusted Publisher, which creates the project on first successful publish.

## Release flow

1. Complete the checklist above.
2. Tag the release as `vX.Y.Z`.
3. Publish the matching GitHub Release.
4. GitHub Actions builds the distributions and publishes them to PyPI through OIDC.
5. Verify the PyPI project page and installation in a fresh environment.

After the first PyPI release, the preferred user install path should become:

```bash
pipx install minit-runtime
```

or:

```bash
uv tool install minit-runtime
```

The installed CLI command remains:

```bash
minit
```
