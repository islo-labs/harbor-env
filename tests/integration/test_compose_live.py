"""Live integration test for IsloEnvironment compose mode.

Spins up a real Islo sandbox, runs ``docker compose up`` against a minimal
multi-file overlay (the user's compose merged with harbor's shared base /
build / no-network templates), and verifies that ``env.exec`` lands inside
the canonical ``main`` service.

The whole module is gated on ``ISLO_API_KEY``; without it the test is
silently skipped, so this file is safe to leave checked in. CI sets the
secret as an env var on the pytest step (see .github/workflows/ci.yml).
"""

import os
from uuid import uuid4

import pytest
from harbor.models.task.config import EnvironmentConfig
from harbor.models.trial.paths import TrialPaths

from harbor_islo import IsloEnvironment

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("ISLO_API_KEY"),
        reason="ISLO_API_KEY not set; live test skipped",
    ),
    pytest.mark.integration,
]


# A minimal compose file shaped like what harbor tasks ship: declare a
# ``main`` service that builds from the task environment dir. The shared
# harbor templates (base / build / no-network / our CA overlay) are
# merged on top at runtime by IsloEnvironment._start_compose.
_COMPOSE_YAML = """\
services:
  main:
    image: ${MAIN_IMAGE_NAME}
    working_dir: /app
"""

# Small image with ``bash`` preinstalled. IsloEnvironment.exec() runs
# commands as ``bash -lc <cmd>`` inside the main service, so the chosen
# base must ship bash -- alpine:3.20 doesn't, debian-slim does.
_DOCKERFILE = """\
FROM debian:12-slim
WORKDIR /app
"""


@pytest.mark.asyncio
async def test_compose_mode_against_real_islo(tmp_path):
    """End-to-end: bring up a compose project on a real Islo VM and exec into it.

    Budget: ~60-90s (sandbox provision + alpine pull + compose up + a couple
    of execs). Uses a uuid-suffixed session id so reruns don't collide.
    """
    env_dir = tmp_path / "environment"
    env_dir.mkdir()
    (env_dir / "docker-compose.yaml").write_text(_COMPOSE_YAML)
    (env_dir / "Dockerfile").write_text(_DOCKERFILE)

    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    trial_paths = TrialPaths(trial_dir=trial_dir)
    trial_paths.mkdir()

    env = IsloEnvironment(
        environment_dir=env_dir,
        environment_name="harbor-islo-compose-test",
        session_id=f"compose-test-{uuid4().hex[:8]}",
        trial_paths=trial_paths,
        task_env_config=EnvironmentConfig(),
    )

    # Sanity: detection logic should have seen the compose file.
    assert env._compose_mode is True

    started = False
    try:
        await env.start(force_build=True)
        started = True

        echo_result = await env.exec(command="echo hello")
        assert echo_result.return_code == 0, (
            f"echo failed: rc={echo_result.return_code} "
            f"stdout={echo_result.stdout!r} stderr={echo_result.stderr!r}"
        )
        assert "hello" in (echo_result.stdout or "")

        os_release = await env.exec(command="cat /etc/os-release")
        assert os_release.return_code == 0, (
            f"cat /etc/os-release failed: rc={os_release.return_code} "
            f"stderr={os_release.stderr!r}"
        )
        # We pinned debian:12-slim; assert we landed in the main service
        # (rather than, say, the islo-runner host VM).
        assert "Debian" in (os_release.stdout or ""), (
            f"unexpected /etc/os-release contents: {os_release.stdout!r}"
        )
    finally:
        # Only stop if start succeeded -- otherwise there's no sandbox to
        # destroy and stop() would no-op anyway, but being explicit avoids
        # masking the real failure with a teardown traceback.
        if started and env._sandbox_name is not None:
            await env.stop(delete=True)
