# Remi

Remi is a restaurant voice-agent backend project for the **SDxSDSU Hackathon**. The goal is to let a guest speak naturally with a restaurant, have an agent understand the request, and safely carry out supported actions through restaurant point-of-sale (POS) systems. The MVP uses a mock POS API for development and benchmarks because the team does not currently have access to an Oracle POS system.

The MVP combines speech recognition (STT), agent orchestration, speech generation (TTS), and restaurant actions in one Python service. LangGraph provides the stateful agent workflow, and LangChain provides model and tool abstractions. ElevenLabs is the planned speech provider. Daytona is available for isolated command execution when a task needs a sandbox; ordinary POS actions should use the service's validated POS adapter directly. The MVP uses deterministic mock POS endpoints and does not require access to a live POS vendor.

## Architecture direction

Use a **single Python FastAPI service** for voice-agent orchestration and restaurant/POS API endpoints. LangGraph defines the agent's stateful workflow and tool execution; LangChain provides model and tool integration abstractions. Keep per-turn context limited to the conversation and restaurant data needed, and use explicit state/checkpoints for multi-step tasks such as building and confirming an order. Async endpoints and clients plus streaming speech reduce avoidable waiting. There is no internal TypeScript/Python service hop. When a real POS provider is integrated in the future, its external network latency will still apply.

### Proposed request flow

1. A caller sends audio or a transcript to the agent service.
2. The FastAPI service handles STT/agent/TTS orchestration; a LangGraph workflow maintains turn state and selects from explicitly defined tools.
3. The service validates any proposed restaurant action and invokes the configured POS adapter directly.
4. The mock POS API returns deterministic results for local development and repeatable benchmarks. A future real POS adapter can implement the same interface.
5. Use Daytona sandboxes only for tasks that need isolated command execution. Sandbox results do not replace POS authorization or server-side validation.

## Repository layout

```text
.
├── services/
│   ├── agent/     # Python + FastAPI plus MCP tools for restaurant actions
│   └── mocks/     # Mock restaurant integration APIs (Oracle POS, 7shifts, MarketMan)
├── pyproject.toml # Python service dependencies
├── uv.lock       # Locked Python dependency versions
├── .venv/        # Local Python virtual environment (not committed)
├── AGENTS.md     # Contributor and coding-agent project guidance
├── README.md     # Project overview and setup
└── doc/
    └── latency-estimates.md # Provider figures and Remi planning estimates
```

## Getting started

Requirements: Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

Install dependencies:

```bash
uv sync
```

`uv sync` creates `.venv/` and installs the locked Python dependencies. Run Python commands with `uv run` so they use this environment.

Run the starter services in separate terminals:

```bash
# Terminal 1: Run mock restaurant integrations server (port 8001)
uv run uvicorn mocks.main:app --app-dir services/mocks --reload --port 8001

# Terminal 2: Run voice agent service (port 8000)
uv run uvicorn agent.main:app --app-dir services/agent --reload --port 8000
```

The FastAPI agent service listens on `http://localhost:8000` and currently exposes a health check. The mock integrations service runs on `http://localhost:8001`, simulating Oracle POS, 7shifts, and MarketMan with realistic latency injection and profiles (`low_latency`, `typical_cloud`, `rush_hour_degraded`).

### MCP tools

The agent package includes a stdio MCP server for the mock services. After copying `.env.example` to `.env`, start it from the repository root with `PYTHONPATH=services/agent uv run --env-file .env python -m agent.mcp_server`. This loads `MOCK_POS_BASE_URL` from `.env`; without `--env-file`, set the variable in the shell yourself. The server provides menu, inventory, item availability, staff, shift, and confirmed order submission tools. MCP stdio is intended for an agent runtime that launches the server as a child process; if the agent runs in Daytona, the mock service URL must be reachable from that sandbox.

## Configuration

Copy `.env.example` to `.env` and adjust local service URLs as needed. Endpoint configuration stays in environment settings for this MVP; a restaurant-facing configuration UI can be added when we support multiple restaurant deployments and have authentication and credential storage. The mock POS API does not require vendor credentials. Add provider credentials only when the corresponding integrations are implemented; never commit secrets. Keep Daytona and provider credentials server-side and do not pass them to the model or expose them to callers.

## Development

```bash
uv run python -m compileall services/agent services/mocks
```

## Documentation

- [AGENTS.md](AGENTS.md) is the contributor and coding-agent guide. It points to the relevant project documentation and records the architecture and implementation conventions.
- [Latency estimates](doc/latency-estimates.md) contains published ElevenLabs measurements, clearly labeled Remi planning estimates, and the proposed benchmark measurements.

## Next steps

- Define the restaurant action schema and authorization rules.
- Connect the MCP tools to a LangGraph workflow with conversation state, scoped permissions, and order confirmation gates.
- Add repeatable benchmarks against the mock POS API; replace or supplement it with a real POS adapter if access becomes available.
- Implement a LangGraph workflow with conversation state, narrow POS tools, and order confirmation gates.
- Add streaming STT/TTS with ElevenLabs and choose an LLM provider integration.
- Add a constrained Daytona execution workflow, audit logging, timeouts, and cancellation.
- Measure end-to-end latency and failure behavior using representative calls and POS operations.
