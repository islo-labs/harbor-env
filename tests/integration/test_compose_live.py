"""Live end-to-end integration test for IsloEnvironment compose mode.

Drives the full Harbor trial pipeline against a real Islo tenant:

* ``Trial.create(...)`` resolves ``environment.import_path`` to
  :class:`harbor_islo.IsloEnvironment` (this is the first time we exercise
  the env class as a third-party plugin through ``EnvironmentFactory``).
* The fixture under ``fixtures/compose-task/`` is a canonical Harbor task
  with ``environment/docker-compose.yaml`` so IsloEnvironment picks
  compose mode automatically.
* The Oracle agent uploads ``solution/`` and runs ``solve.sh`` inside the
  ``main`` compose service, writing the marker the verifier looks for.
* The verifier uploads ``tests/`` and runs ``test.sh``, which asserts the
  marker and writes ``/logs/verifier/reward.txt``.
* We then assert ``trial.run()`` returned a verifier reward of 1.0 and
  that the sandbox was destroyed (``delete=True`` is the trial default).

Gated on ``ISLO_API_KEY`` -- without it the test is silently skipped, so
this file is safe to leave checked in. CI sets the secret as an env var
on the pytest step (see ``.github/workflows/ci.yml``).
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

FIXTURE_TASK = Path(__file__).parent / "fixtures" / "compose-task"


@pytest.mark.asyncio
async def test_oracle_trial_against_real_islo_compose(tmp_path: Path) -> None:
    """End-to-end: Oracle + IsloEnvironment(compose) + verifier on a real VM.

    Budget: ~3-5 minutes. The bulk of the time is sandbox provisioning,
    base-image pull, ``docker compose build`` of debian:12-slim, then the
    actual oracle/verifier exec round-trips. ``ISLO_API_KEY`` must be set;
    otherwise the test is skipped.
    """
    # Copy the fixture into tmp_path so concurrent reruns don't fight over
    # the same on-disk task directory and so the trial is free to write
    # alongside it without polluting the repo.
    task_dir = tmp_path / "compose-task"
    shutil.copytree(FIXTURE_TASK, task_dir)
    # copytree drops the executable bit on Windows hosts and on some CI
    # tarball checkouts; restore it explicitly so verifier/oracle don't
    # need to chmod the scripts they themselves uploaded.
    (task_dir / "solution" / "solve.sh").chmod(0o755)
    (task_dir / "tests" / "test.sh").chmod(0o755)

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
