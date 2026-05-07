# Live integration tests

These tests exercise `harbor_islo.IsloEnvironment` against a **real Islo
tenant**. They provision sandboxes, build images, and run compose stacks
or Docker-in-VM containers -- the end-to-end suite
(`test_islo_modes_live.py`) drives the full Harbor `Trial` pipeline
(Oracle agent + verifier + sandbox teardown) across all three
`IsloEnvironment` modes. Each run consumes Islo VM time on your account.

## Tests in this directory

`test_islo_modes_live.py` contains one test per mode -- each test boots a
fresh sandbox, runs an Oracle trial against a fixture under `fixtures/`,
and asserts a verifier reward of 1.0. Three separate test functions so
failures stay discoverable per-mode in CI logs.

| Test                                | Mode       | Fixture              | Wall-clock |
| ----------------------------------- | ---------- | -------------------- | ---------- |
| `test_oracle_trial_compose_mode`    | Compose    | `compose-task/`      | ~40s       |
| `test_oracle_trial_dockerfile_mode` | Dockerfile | `dockerfile-task/`   | ~30-90s    |
| `test_oracle_trial_prebuilt_mode`   | Prebuilt   | `prebuilt-task/`     | ~15-30s    |

Prebuilt is the fastest -- just sandbox provisioning and a base-image
pull, no Docker-in-VM build step. Dockerfile is next -- the in-VM Docker
daemon has to start, pull `debian:12-slim`, and run a full `docker build`
before exec-ing into the container. Compose is the slowest at the small
end because the in-VM compose stack has to come up after the build.
Numbers above are observed locally; CI may be slower if the Islo region
is far from the runner.

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

To run a single mode:

```sh
ISLO_API_KEY=… uv run pytest tests/integration/test_islo_modes_live.py::test_oracle_trial_prebuilt_mode -v -s
```

## Running in CI

`.github/workflows/ci.yml` passes `ISLO_API_KEY` from repo secrets into the
pytest step. When the secret is configured, the integration tests run on
every push / PR. When it isn't, they skip silently and CI stays green --
this is intentional so external contributors' PRs don't fail because they
can't see the secret.
