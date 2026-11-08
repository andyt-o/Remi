# Remi contributor and coding-agent guide

Read this file before making project changes. Use the linked documents for their stated scope and keep them consistent when architecture or setup changes.

## Documentation map

- [README.md](README.md): project purpose, current MVP architecture, setup, and next steps. Keep it concise and aimed at onboarding.
- [Latency estimates](doc/latency-estimates.md): sourced ElevenLabs measurements, Remi planning assumptions, and the measurement plan. Keep provider-published numbers separate from estimates and actual benchmark results.
- [MCP server](services/agent/agent/mcp_server.py): tool definitions and validation for the mock restaurant integrations. Keep tools narrowly scoped; require caller confirmation before creating an order check.
- [.env.example](.env.example): names and safe local defaults for configuration. Never put real credentials in this file.
- [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock): Python dependency declarations and exact resolved dependency graph. Change dependencies through `uv` and commit both files together.

Before adding a new document, check whether the information belongs in one of these existing files. Link new project documentation from this guide and from the README when it is useful for onboarding.

## Current project direction

- Remi is an SDxSDSU Hackathon restaurant voice-agent backend MVP.
- Use Python and FastAPI for the service, with LangGraph for stateful agent workflows and LangChain for model/tool abstractions.
- Keep agent orchestration and POS adapter calls in the same service process. Do not reintroduce a TypeScript service or an internal service hop without an explicit architecture change.
- Use deterministic mock POS endpoints for MVP development and repeatable benchmarks. Do not add Oracle credentials or imply that a live Oracle POS integration is available.
- Expose restaurant operations through the Python MCP server in `services/agent/agent/mcp_server.py`; configure the mock service URL with `MOCK_POS_BASE_URL`. For Daytona execution, that URL must be reachable from inside the sandbox.
- Keep endpoint URLs in environment configuration for the hackathon MVP. A configuration UI requires a defined multi-restaurant deployment model, authentication, and protected credential storage first.
- ElevenLabs is the planned speech provider. Daytona is optional and only for tasks requiring isolated command execution; do not place ordinary POS requests through a sandbox.
- Keep model-proposed actions behind server-side validation and narrowly scoped tools. Treat transcripts, model output, and sandbox output as untrusted input.

## Python environment and workflow

- Use `uv` to manage Python dependencies and the repository `.venv`.
- Run the service with:

  ```bash
  uv run uvicorn agent.main:app --app-dir services/agent --reload --port 8000
  ```

- Run Python commands through `uv run` so they use the project environment.
- To launch the MCP server with repository configuration, run `PYTHONPATH=services/agent uv run --env-file .env python -m agent.mcp_server` from the repository root. `uv run` does not automatically load `.env` unless `--env-file .env` is supplied.
- When changing dependencies, update `pyproject.toml` and regenerate `uv.lock` with `uv lock`; sync with `uv sync --locked`.
- Keep secrets out of source control. Add only variable names and safe defaults to `.env.example`.

## Keeping docs accurate

- When architecture, setup, ports, or environment variables change, update README.md and `.env.example` in the same change.
- When latency assumptions, measurement definitions, or provider model references change, update `doc/latency-estimates.md` and cite current authoritative sources for vendor claims.
- Label values as **provider-published**, **Remi estimate**, or **Remi measured**. Never present estimates as benchmark results.
- Mock POS benchmarks measure the local Remi path; clearly state that they do not measure future vendor POS latency.
- After editing docs, scan for stale architecture and setup references, including TypeScript, Fastify, npm, Oracle credentials, and obsolete ports.
