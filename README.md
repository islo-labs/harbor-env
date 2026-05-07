# harbor-islo

Islo microVM sandbox plugin for the Harbor agent-evaluation framework.

## Why this exists

`harbor-islo` packages the `IsloEnvironment` as a standalone plugin so Islo
users can iterate on the integration independently of the upstream Harbor
release cadence. v0.1 ships the same Islo environment that's currently bundled
with Harbor upstream — the value is shipping it on its own release train so we
can move faster on Islo-specific features.

## Install

```bash
pip install harbor-islo
```

Requires `harbor >= 0.6`.

## Quickstart

Define an inline gateway policy in the task / job config (recommended — the
policy lives next to the run that uses it, no out-of-band setup):

```yaml
environment:
  import_path: "harbor_islo:IsloEnvironment"
  kwargs:
    gateway:
      default_action: "deny"
      rules:
        - host_pattern: "api.openai.com"
          action: "allow"
          provider_key: "openai"
        - host_pattern: "*.github.com"
          action: "allow"
```

Or reference a named gateway profile that's been pre-created in the Islo
control plane (useful when many runs share the same policy):

```yaml
environment:
  import_path: "harbor_islo:IsloEnvironment"
  kwargs:
    gateway_profile: "prod-apis"
```

## CLI

```bash
harbor run \
  --environment-import-path harbor_islo:IsloEnvironment \
  --dataset terminal-bench@2.0 \
  --agent claude-code \
  --model anthropic/claude-opus-4-1
```

Authenticate against the Islo control plane by setting `ISLO_API_KEY` to
your Islo API key. Override the API endpoint with `ISLO_API_URL` if you're
not pointed at production.

## Compatibility

- `harbor >= 0.6`
- Python 3.12+

## Roadmap

- v0.2: phased gateway — per-phase policy that flips at trial-lifecycle
  boundaries (setup / agent / verifier). Blocked on upstream Harbor exposing
  the lifecycle hooks needed to drive it.
