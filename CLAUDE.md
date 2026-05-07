# CLAUDE.md

`harbor-islo` is a standalone pip package wrapping Harbor's Islo environment so we can iterate without waiting for upstream Harbor releases. Users invoke it via `harbor run --environment-import-path harbor_islo:IsloEnvironment …`.

## Releasing

Tag-driven publish to PyPI via OIDC trusted publishing. Bump `version` in `pyproject.toml`, commit on `main`, then `git tag v$VERSION && git push --tags`. The `Publish to PyPI` workflow builds + uploads, gated on the `pypi` GitHub Environment which requires manual approval.

## Source

Source lives in `src/harbor_islo/environment.py` (ported from harbor upstream's `src/harbor/environments/islo.py`, with `EnvironmentType` dropped and `type()` returning `"islo"`). Unit tests in `tests/test_environment.py` mock the islo SDK; live integration tests in `tests/integration/test_islo_modes_live.py` cover all three `IsloEnvironment` modes (compose, Dockerfile, prebuilt) by running real `Trial`+oracle+verifier flows against a real Islo tenant. The whole `tests/integration/` directory is skip-gated on `ISLO_API_KEY` and tagged `@pytest.mark.integration`; CI passes the secret from repo settings into the pytest step. Run locally with `ISLO_API_KEY=… uv run pytest tests/integration/ -v -s`.
