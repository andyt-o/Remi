# Remi

Remi is a restaurant voice-agent backend project for the **SDxSDSU Hackathon**. The goal is to let a guest speak naturally with a restaurant, have an agent understand the request, and safely carry out supported actions through existing restaurant point-of-sale (POS) systems such as Oracle POS.

The system is expected to connect speech recognition (STT), an agent/harness, speech generation (TTS), restaurant APIs, and an isolated command-execution environment. ElevenLabs is the planned speech provider, and Daytona is the planned environment for creating VMs used by agents to execute commands. These are integration targets; credentials and working vendor integrations are not included yet.

## Architecture direction

Start with a **TypeScript API service using Fastify** for latency-sensitive restaurant and POS endpoints. Fastify is a good fit for a small, async HTTP service and offers a lighter request path than Express in published framework benchmarks. Benchmark real Remi routes before treating framework benchmark numbers as a product result. Express remains a reasonable choice if the team values its familiarity or middleware ecosystem more than a small framework-level overhead difference.

Use a **Python agent service (FastAPI)** for the voice-agent orchestration and provider integrations where Python libraries are useful. Keep speech and model calls asynchronous and stream audio/results where supported. Do not route every POS request through Python just because the agent service uses Python.

A service boundary has a cost: an extra network or IPC hop, serialization, and another service to run. On one machine, loopback HTTP is usually simpler than custom IPC; in deployment, use a private network. The external STT, LLM, TTS, and POS calls are likely to dominate end-to-end conversational latency, but measure the actual path. If the Python service is only a thin pass-through and the team does not need Python-specific tooling, consolidate into TypeScript to remove the hop. For the hackathon foundation, the two-service split keeps the fast POS API path direct while leaving agent orchestration in Python.

### Proposed request flow

1. A caller sends audio or a transcript to the agent service.
2. The agent service handles STT/agent/TTS orchestration and determines an allowed restaurant action.
3. The agent calls the TypeScript API over a private HTTP interface for POS operations.
4. The API validates the request and invokes the configured POS adapter.
5. Daytona-created VMs, when used, should execute only narrowly scoped agent commands; they are not a substitute for POS authorization or server-side validation.

## Repository layout

```text
.
├── services/
│   ├── api/       # TypeScript + Fastify restaurant/POS API
│   └── agent/     # Python + FastAPI voice-agent service
├── package.json  # Workspace scripts and API dependencies
├── pyproject.toml # Python agent dependencies
├── uv.lock       # Locked Python dependency versions
└── .venv/        # Local Python virtual environment (not committed)
    README.md
```

## Getting started

Requirements: Node.js 20 or newer, npm, Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/).

Install dependencies:

```bash
npm install
uv sync
```

`uv sync` creates `.venv/` and installs the locked Python dependencies. Run Python commands with `uv run` so they use this environment.

Run the starter services in separate terminals:

```bash
npm run dev:api
uv run uvicorn agent.main:app --app-dir services/agent --reload --port 8000
```

The API listens on `http://localhost:3000`; the agent service listens on `http://localhost:8000`. The initial services expose health checks only. The Python environment includes the Daytona and ElevenLabs SDKs, but credentials and working provider adapters still need to be configured and implemented.

## Configuration

Copy `.env.example` to `.env` and fill in credentials when the corresponding integrations are implemented. Never commit secrets. Keep Daytona execution credentials and POS credentials server-side; do not pass them to the model or expose them to callers.

## Development

```bash
npm run typecheck
uv run python -m compileall services/agent
```

## Next steps

- Define the restaurant action schema and authorization rules.
- Add a POS adapter interface, then implement and validate an Oracle POS integration against its supported API and sandbox.
- Add streaming STT/TTS and agent orchestration with ElevenLabs.
- Add a constrained Daytona execution workflow, audit logging, timeouts, and cancellation.
- Measure end-to-end latency and failure behavior using representative calls and POS operations.
