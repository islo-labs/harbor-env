"""Live end-to-end integration tests for IsloEnvironment, all three modes.

Each test drives the full Harbor trial pipeline (``Trial.create`` →
``Trial.run`` → reward assertion) against a real Islo tenant, exercising
``harbor_islo.IsloEnvironment`` as a third-party plugin loaded through
``EnvironmentFactory`` via ``environment.import_path``.

The three modes covered correspond to the dispatch in
:meth:`IsloEnvironment.start`:

* **compose mode** -- ``environment/docker-compose.yaml`` present.  The
  sandbox boots the default islo-runner with the ``docker`` capability and
  runs a compose stack with a ``main`` service.
* **dockerfile mode** -- ``environment/Dockerfile`` present, no compose.
  The sandbox boots, the docker daemon comes up, ``docker build`` runs
  against the uploaded build context, then ``docker run`` starts the built
  image.  ``exec()`` calls go through ``docker exec``.
* **prebuilt mode** -- ``task_env_config.docker_image`` set, no Dockerfile
  and no compose.  The sandbox is created with ``image=<docker_image>``
  directly; no Docker-in-VM, no compose stack.

Each test uses the Oracle agent (uploads ``solution/`` and runs
``solve.sh``) and the standard verifier (uploads ``tests/`` and runs
``test.sh`` which writes ``/logs/verifier/reward.txt``).

Gated on ``ISLO_API_KEY`` -- without it, every test in this module is
skipped at collection time, so the file is safe to leave checked in.  CI
sets the secret as an env var on the pytest step (see
``.github/workflows/ci.yml``).
"""

import os
import shutil
from pathlib import Path

import pytest
from harbor.models.agent.name import AgentName
from harbor.models.trial.config import (
    AgentConfig,
    EnvironmentConfig,
    TaskConfig,
    TrialConfig,
)
from harbor.trial.trial import Trial

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("ISLO_API_KEY"),
        reason="ISLO_API_KEY not set; live test skipped",
    ),
    pytest.mark.integration,
]

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_COMPOSE = FIXTURES_DIR / "compose-task"
FIXTURE_DOCKERFILE = FIXTURES_DIR / "dockerfile-task"
FIXTURE_PREBUILT = FIXTURES_DIR / "prebuilt-task"


async def _run_trial_and_assert_reward_one(tmp_path: Path, fixture_dir: Path) -> None:
    """Copy *fixture_dir* into *tmp_path*, run a full Trial, assert reward=1.0.

    Pulled out because all three mode tests want exactly the same shape:
    an Oracle trial against IsloEnvironment with ``force_build=True`` and
    ``delete=True`` on a copy of a canonical Harbor task. The only thing
    that differs between modes is which fixture is on disk -- compose,
    Dockerfile, or prebuilt-image task.toml -- and that selection is
    *itself* what triggers the different code paths inside
    :meth:`IsloEnvironment.start`.
    """
    # Copy the fixture into tmp_path so concurrent reruns don't fight over
    # the same on-disk task directory and so the trial is free to write
    # alongside it without polluting the repo.
    task_dir = tmp_path / fixture_dir.name
    shutil.copytree(fixture_dir, task_dir)
    # copytree drops the executable bit on Windows hosts and on some CI
    # tarball checkouts; restore it explicitly so verifier/oracle don't
    # need to chmod the scripts they themselves uploaded. The prebuilt
    # fixture has no Dockerfile so we guard with .exists() rather than
    # asserting layout.
    solve_path = task_dir / "solution" / "solve.sh"
    test_path = task_dir / "tests" / "test.sh"
    if solve_path.exists():
        solve_path.chmod(0o755)
    if test_path.exists():
        test_path.chmod(0o755)

    config = TrialConfig(
        task=TaskConfig(path=task_dir),
        agent=AgentConfig(name=AgentName.ORACLE.value),
        environment=EnvironmentConfig(
            import_path="harbor_islo:IsloEnvironment",
            force_build=True,
            delete=True,
        ),
        trials_dir=tmp_path / "trials",
    )

    trial = await Trial.create(config=config)
    result = await trial.run()

    assert result.exception_info is None, f"Trial raised: {result.exception_info!r}"
    assert result.verifier_result is not None, (
        "Verifier never produced a result -- the verifier step did not run "
        "or failed before writing /logs/verifier/reward.txt."
    )
    rewards = result.verifier_result.rewards or {}
    assert rewards.get("reward") == 1.0, (
        f"Expected oracle path to score reward=1.0, got rewards={rewards!r}. "
        f"Trial dir: {result.trial_uri}"
    )

    # Sandbox cleanup: with ``environment.delete=True`` (default), the env's
    # ``stop()`` should have destroyed the sandbox. We can't query islo
    # directly here without coupling the test to the SDK, but we can at
    # least confirm Trial finished cleanly with no lingering exception.
    assert result.finished_at is not None


@pytest.mark.asyncio
async def test_oracle_trial_compose_mode(tmp_path: Path) -> None:
    """End-to-end: Oracle + IsloEnvironment(compose) + verifier on a real VM.

    Budget: ~40s observed locally. Sandbox provisioning + base-image pull
    + ``docker compose build`` of debian:12-slim + oracle/verifier
    round-trips. The fixture's ``environment/docker-compose.yaml`` is what
    causes IsloEnvironment to pick the compose code path.
    """
    await _run_trial_and_assert_reward_one(tmp_path, FIXTURE_COMPOSE)


@pytest.mark.asyncio
async def test_oracle_trial_dockerfile_mode(tmp_path: Path) -> None:
    """End-to-end: Oracle + IsloEnvironment(Dockerfile) + verifier on a real VM.

    Budget: ~30-90s observed locally. Sandbox provisioning + waiting for
    the in-VM Docker daemon + ``docker build`` from the uploaded context
    + ``docker run`` + oracle/verifier round-trips. The fixture has
    ``environment/Dockerfile`` and no ``docker-compose.yaml``, which
    causes IsloEnvironment to pick the Docker-in-VM code path.
    """
    await _run_trial_and_assert_reward_one(tmp_path, FIXTURE_DOCKERFILE)


@pytest.mark.asyncio
async def test_oracle_trial_prebuilt_mode(tmp_path: Path) -> None:
    """End-to-end: Oracle + IsloEnvironment(prebuilt) + verifier on a real VM.

    Budget: ~15-30s observed locally -- fastest of the three because
    there's no Docker build step inside the sandbox; the sandbox is
    created with ``image=python:3.13-slim`` directly. The fixture has
    ``[environment].docker_image`` set in ``task.toml`` and no Dockerfile
    or compose file, which causes IsloEnvironment to pick the prebuilt
    code path.
    """
    await _run_trial_and_assert_reward_one(tmp_path, FIXTURE_PREBUILT)
