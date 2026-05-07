# Live integration tests

These tests exercise `harbor_islo.IsloEnvironment` against a **real Islo
tenant**. They provision sandboxes, build images, and run compose stacks --
each run takes ~60-90 seconds and consumes Islo VM time on your account.

## Gating

The whole `tests/integration/` directory is gated on `ISLO_API_KEY`:

- If `ISLO_API_KEY` is **unset**, every test in this directory is skipped at
  collection time (`pytest.mark.skipif`). `pytest tests/` is therefore safe
  to run with no key configured.
- If `ISLO_API_KEY` **is** set, the tests run against
  `https://api.islo.dev` (or `ISLO_API_URL` if you override it).

Each test is also tagged `@pytest.mark.integration` so you can opt out
explicitly:

```sh
pytest tests/ -v -m "not integration"
```

## Running locally

```sh
ISLO_API_KEY=… uv run pytest tests/integration/ -v -s
```

`-s` is recommended so you can watch the env's debug output (sandbox
creation, docker build progress, compose up, etc.) in real time. A failing
test will leak its sandbox if you `Ctrl-C` mid-test -- check the Islo
console and clean up manually if needed.

## Running in CI

`.github/workflows/ci.yml` passes `ISLO_API_KEY` from repo secrets into the
pytest step. When the secret is configured, the integration tests run on
every push / PR. When it isn't, they skip silently and CI stays green --
this is intentional so external contributors' PRs don't fail because they
can't see the secret.
