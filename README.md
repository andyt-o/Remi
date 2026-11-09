# Remi

Remi is a restaurant staff voice-agent project for the **SDxSDSU Hackathon**. Its primary goal is to help front-of-house and management staff coordinate operational tasks, such as preparing next week's shift schedule for a manager to review and manually approve. Server-to-guest order conversations remain a separate workflow. The MVP uses mock POS and restaurant-integration APIs with seeded data for development and benchmarks because the team does not currently have access to live vendor systems.

The MVP is developing a voice workflow around a Python service, with desktop speech recognition, agent turns, speech generation (TTS), and mock restaurant operations. LangGraph provides the stateful agent workflow, and LangChain provides model and tool abstractions. ElevenLabs is the planned speech provider. Daytona is available for isolated command execution when a task needs a sandbox; ordinary restaurant operations should use the service's validated adapters directly. The MVP uses mock integrations with seeded data and does not require access to live vendors.

## Architecture direction

Use a **single Python FastAPI service** for voice-agent orchestration and restaurant/POS API endpoints. LangGraph defines the agent's stateful workflow and tool execution; LangChain provides model and tool integration abstractions. Keep per-turn context limited to the conversation and restaurant data needed, and use explicit state/checkpoints for multi-step tasks such as building and confirming an order. Async endpoints and clients plus streaming speech reduce avoidable waiting. There is no internal TypeScript/Python service hop. When a real POS provider is integrated in the future, its external network latency will still apply.

### Proposed request flow

1. A staff member sends a voice request to coordinate an operational task; a separate server-to-guest workflow can capture order requests.
2. The FastAPI service handles STT/agent/TTS orchestration; a LangGraph workflow maintains turn state and selects from explicitly defined tools.
3. The service validates proposed restaurant actions. Staff schedules are prepared as drafts and require manual manager approval before any future write; guest orders require guest confirmation.
4. Fast memory caching (TTL cache) keeps static data (menus, rosters) instantly readable (<1ms) without repeated network hops, while volatile actions (checks, 86 availability checks) query live endpoints directly.
5. The mock POS API supplies seeded data for local development; latency and degraded-profile failures are randomized. A future real POS adapter can implement the same interface.
6. Use Daytona sandboxes only for tasks that need isolated command or code execution (e.g. ad-hoc reporting scripts or data crunching). Ordinary live voice turns and POS operations run directly in the service process to protect the sub-second audio path.

## Data synchronization and execution boundaries

To preserve sub-second voice latency across live conversational turns:

- **Audio path latency:** The initial target is under 1 second p50 and 1.5 seconds p95 to first audio; this has not yet been measured. Placing container startup or cloud sandbox hops on this direct loop causes dead air.
- **In-memory TTL cache:** Static and slow-changing data (menus, pricing, staff directory) is held in memory with a short Time-To-Live (e.g. 15–30 minutes). A cache read is intended to take **under 1 millisecond**, allowing the agent to answer menu questions without network latency.
- **On-demand verification:** High-volatility operational state (open checks, real-time 86'd stock availability, order placement) bypasses the cache and queries or mutates endpoints with zero TTL.
- **Daytona isolation:** Daytona sandboxes provide isolated container environments for executing untrusted, background, or analytical code (such as ad-hoc manager sales analysis scripts, invoice data parsing, or reconciliation jobs). They are not used as an intermediary layer for ordinary POS or voice turns.

## Repository layout

```text
.
├── services/
│   ├── agent/     # Python + FastAPI plus MCP tools for restaurant actions
│   └── mocks/     # Mock restaurant integration APIs (Oracle POS, 7shifts, MarketMan)
├── public/       # Shared Remi logo and menu category SVG icons
├── apps/
│   └── desktop/   # Electron + Vite cross-platform MVP demonstration UI
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

The desktop demonstration uses Node.js 20+ and npm. Install its dependencies once:

```bash
cd apps/desktop
npm install
```

`uv sync` creates `.venv/` and installs the locked Python dependencies. Run Python commands with `uv run` so they use this environment.

Run the starter services in separate terminals:

```bash
# Terminal 1: Run mock restaurant integrations server (port 8001)
uv run --env-file .env uvicorn mocks.main:app --app-dir services --reload --port 8001

# Terminal 2: Run voice agent service (port 8000)
uv run --env-file .env uvicorn agent.main:app --app-dir services/agent --reload --port 8000
```

Start the desktop app in a third terminal from `apps/desktop`:

```bash
npm start
```

The Electron UI opens as a cross-platform desktop window with a demo sign-on and role-specific onboarding. Its Overview focuses on automated front-of-house tasks, agent/API health, mock backend connectors, and ElevenLabs/Daytona integration status. The central Staff assistant page contains the microphone, transcript, agent context, and a schedule-draft review flow with manual manager approval. Guest calls remain in their own server-to-guest area. Starting a staff session adds “What should we do today {{role}}, {{user}}?” to the transcript and requests ElevenLabs TTS from the FastAPI service; the staff microphone listens continuously during an active session, detects speech and pauses locally, and sends captured utterances to the agent service for ElevenLabs transcription and TTS playback. Spoken stop requests require “confirm stop”; the mic button stops immediately. During playback, captured speech is transcribed to detect interruption phrases such as “Remi, stop”; other speech is ignored. Detection occurs after an utterance and depends on ElevenLabs and background noise. Typed staff requests also reach the agent, and the menu page reads the mock POS through the selected demo account. The schedule proposal and approval are local demo states and are not written to 7shifts. Settings includes Connections, Voice agent, Daytona, Agent instructions, and Workplace instructions. Connection URLs and credentials remain backend environment settings; voice style, sandbox controls, and instructions are demo-local and not yet persisted or applied to the backend prompt.

The FastAPI agent service listens on `http://localhost:8000` and exposes health checks plus `POST /voice/greeting` for ElevenLabs session greeting TTS. The mock integrations service runs on `http://localhost:8001`, simulating Oracle POS, 7shifts, and MarketMan with realistic latency injection and profiles (`low_latency`, `typical_cloud`, `rush_hour_degraded`). The menu response includes a relative `icon_url` for each item; the mock server serves category SVGs at `http://localhost:8001/menu/{filename}`. Shared icons cover entrees, appetizers, sides, salads, drinks, and desserts; multiple items in a category use the same icon. The shared `public/` directory also contains the Remi logo used by the desktop window and packaged build.

### MCP tools

The agent package includes a stdio MCP server for the mock services. The staff graph calls validated MCP read functions directly for menu, working staff, today’s shifts, inventory, and account status, using the selected desktop demo account. A configured model can also select parameterized availability, check, staff-account, reply, and Daytona status reads for natural requests; server-side checks resolve that account against the mock directory and enforce its role. Ask “check your MCP capabilities” to hear the account and available reads. A manager can ask Remi to start a Daytona delivery report and then ask for its status; the task uses mock data and creates no purchase order. With a configured model, a manager can prepare an SMS alert using a phone number, carrier, and message; Remi reads back the full draft and destination and dispatches only after “confirm send”. “Cancel alert” discards it. Resend sends email to a carrier gateway, so acceptance does not establish phone delivery. Other voice mutations are not connected. After copying `.env.example` to `.env`, start it from the repository root with `PYTHONPATH=services/agent uv run --env-file .env python -m agent.mcp_server`. This loads the mock URL and MCP account ID from `.env`. MCP stdio is intended for an agent runtime that launches the server as a child process; if the agent runs in Daytona, the mock service URL must be reachable from that sandbox.

The desktop passes the selected preset profile's mock account ID to the agent. The agent looks up its role and active status in the mock staff directory for each request, and isolates conversation history by account and session. Taylor (106) is a manager; Jordan (105), Elena (102), and Dave (101) have non-manager tool access. The standalone stdio MCP process instead uses `REMI_MCP_ACCOUNT_ID` from `.env`. `get_my_account_status` reports the account used for the current call. Demo profile selection is not authentication: a client can claim any mock account ID. A shared deployment needs authenticated client identity and tenant-aware authorization.

Available MCP tools map to the mock API routes below:

| MCP tool | Mock service route | Access |
| --- | --- | --- |
| `get_my_account_status` | `GET /7shifts/v2/users/{account_id}` | Any demo account |
| `get_menu` | `GET /oracle-pos/menu` | Active staff |
| `create_order_check` | `POST /oracle-pos/checks` | Active staff; call only after guest confirmation |
| `get_order_check` | `GET /oracle-pos/checks/{check_id}` | Active staff |
| `check_item_availability` | `GET /marketman/v1/inventory/check-availability/{item_key}` | Active staff |
| `get_inventory` | `GET /marketman/v1/inventory/items` | Manager |
| `deplete_inventory` | `POST /marketman/v1/inventory/deplete` | Manager; call only after manager confirmation |
| `get_staff_working_now` | `GET /7shifts/v2/who_is_working_now` | Manager |
| `get_today_shifts` | `GET /7shifts/v2/shifts/today` | Manager |
| `update_shift_schedule` | `PUT /7shifts/v2/shifts/{shift_id}` | Manager; requires `expected_version` concurrency check |
| `send_staff_sms_alert` | `POST /notifications/sms` (or Resend/SMTP) | Manager; sends SMS formatted with human manager signature & floor callback number |
| `check_staff_sms_replies` | In-memory reply store / webhook | Manager; checks recent incoming text responses from staff |
| `get_staff_account_status` | `GET /7shifts/v2/users/{user_id}` | Manager |
| `start_daytona_delivery_report` | Background mock inventory report in Daytona | Manager |
| `get_daytona_task` | Read a task and its sandbox lifecycle | Manager |
| `list_daytona_tasks` | List tasks and sandbox lifecycle | Manager |

Daytona MCP tasks use the credentials and in-memory task registry of the MCP process. The separate agent API process has its own registry; task IDs cannot be looked up across processes, and tasks are lost on restart. Sandbox status is the last lifecycle event observed by Remi, not a live Daytona status query; `deletion_requested` does not confirm deletion, and `cleanup_failed` requires operator attention. The task is a bounded report using mock data, and no purchase order is created.

The MCP server exposes these functions as tools to an MCP client; it is not a shell-command interface. Inventory depletion and order submission change mock state. Their tool descriptions require human confirmation, but the MCP server does not verify a confirmation record. Schedule updates also write immediately after role and version checks. Server-side confirmation and revalidation remain to be implemented. Account status (`active`/`disabled`) is separate from shift status (`active`/`break`).

### Manager-controlled staff access (planned)

The manager is the parent administrator for the restaurant workspace and should be able to configure each staff member's access to Remi: which assistant workflows they can use and which MCP tools are available to their client. For example, a manager may allow a server to check menu and item availability while withholding staff roster, shift, inventory, schedule-editing, or other management tools. These settings should be scoped to the restaurant and individual staff account, with role-based defaults that managers can narrow or expand within the limits of their own authority.

The Electron dashboard includes a **Management** page for elevated demo roles (Manager, Shift Lead, and Head Chef). It shows the workplace staff roster, configured workflow/tool access counts, and a link to edit each member's access. In the Manager demo profile, the access editor configures each other preset staff profile's enabled state, assistant workflows, and individual MCP tools. The selections persist in that desktop profile's local storage. This is a UI prototype only: the MCP tool list is still fixed in code and backend access is enforced only by the account's broad server/manager role. The manager can edit access; other elevated roles currently see the roster read-only. These local settings do not change backend permissions.

For production authorization, configured access must be stored and enforced server-side on every tool call; hiding a tool in the client or relying on agent instructions is not authorization. Only an authenticated manager can change staff access, and a manager must not grant access beyond the restaurant's policy ceiling. Disabling an account must revoke tool access immediately.

Guardrails for implementation: use deny-by-default permissions and least privilege; distinguish read tools from state-changing tools; require explicit confirmation for consequential actions (including order submission, inventory depletion, and schedule changes); validate the confirmed action and current permission again at execution time; scope staff and restaurant data to the authenticated tenant; record manager policy changes and tool mutations in an audit log; and provide a safe way to revoke or roll back configuration. Treat manager-authored instructions as guidance, never as a substitute for these checks. For the hackathon MVP, continue using the fixed role checks described above and do not claim per-user configurable permissions are live.

## Configuration

Copy `.env.example` to `.env` and adjust local service URLs as needed. Set `ELEVENLABS_API_KEY` to enable spoken session greetings and agent replies; `ELEVENLABS_VOICE_ID` defaults to a demo voice and can be set to a voice available to your account. Restart the agent service after changing `.env`. Optional `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` configure the model; without a key the graph uses deterministic demo responses. The mock service supplies restaurant data, ElevenLabs is needed for voice replies, and Daytona is needed for the background sandbox report. Endpoint configuration stays in environment settings for this single-restaurant MVP; a restaurant-facing configuration UI requires multi-restaurant deployment, authentication, and protected credential storage. The mock POS API does not require vendor credentials. Never commit secrets. Keep Daytona and provider credentials server-side and do not pass them to the model or expose them to callers.

## Development

```bash
uv run python -m compileall services/agent services/mocks
```

## Documentation

- [AGENTS.md](AGENTS.md) is the contributor and coding-agent guide. It points to the relevant project documentation and records the architecture and implementation conventions.
- [Latency estimates](doc/latency-estimates.md) contains published ElevenLabs measurements, clearly labeled Remi planning estimates, and the proposed benchmark measurements.
- [Desktop app](apps/desktop/README.md) documents the Electron MVP UI and its development commands.
- [UI aesthetics](docs/ui.md) records the current typography, palette, icon style, layout, and interaction conventions.

## Next steps

- Extend the existing staff voice-turn endpoint beyond its limited read tools and add server-side confirmation and manager approval for schedule writes; keep guest order confirmation in its separate workflow.
- Add repeatable benchmarks against the mock POS API; replace or supplement it with a real POS adapter if access becomes available.
- Add streaming STT/TTS with ElevenLabs and choose an LLM provider integration.
- Extend the Daytona MarketMan delivery report with durable task storage, audit logging, cancellation, and production MarketMan history access.
- Measure end-to-end latency and failure behavior using representative calls and POS operations.
