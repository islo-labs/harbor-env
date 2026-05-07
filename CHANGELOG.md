# Changelog

## 0.2.0 — Docker Compose support

- Ports the docker-compose mode from upstream harbor PR harbor-framework/harbor#1559: multi-service tasks defined via `docker-compose.yaml` now run inside the Islo VM via Docker Compose, taking priority over Dockerfile and prebuilt-image paths.
- `EnvironmentCapabilities(disable_internet=True)` is advertised when running in compose mode (the only mode that can currently honor `allow_internet=False`, via the shared `docker-compose-no-network.yaml` overlay).
- New harbor imports the package now relies on (both public, available since harbor 0.3):
  - `harbor.environments.docker.{COMPOSE_BASE_PATH, COMPOSE_BUILD_PATH, COMPOSE_PREBUILT_PATH, COMPOSE_NO_NETWORK_PATH}`.
  - `harbor.utils.env.resolve_env_vars` — resolves `${VAR}` templates in `[environment.env]` for compose mode.
- `_sanitize_docker_image_name` is inlined from harbor (Apache-2.0) so the package has zero private-API dependencies.
- Harbor floor unchanged at `harbor>=0.6`.

## 0.1.0 — Initial release

- `IsloEnvironment` packaged as a standalone plugin, importable via `harbor_islo:IsloEnvironment`.
- Supports the same `gateway_profile` (named) and `gateway` (inline single-policy) kwargs as upstream Harbor's bundled Islo env.
- Targets harbor >=0.6.
