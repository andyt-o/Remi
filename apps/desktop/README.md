# Remi Desktop

Cross-platform Electron demonstration UI for the Remi restaurant voice-agent MVP. The renderer is React + Vite; Electron hosts it in a hardened window with Node integration disabled.

The interface uses Verdana, Heroicons-inspired outline SVGs, and a warm terracotta palette. The app icon and favicon are derived from the repository's Remi chef artwork and use generic `remi-*` names under `assets/icons/`.

The app opens to a demo sign-on screen with preset Server, Manager, Shift Lead, and Head Chef profiles. Each profile has role-specific onboarding before entering the workspace. Overview focuses on front-of-house automation, API health, backend connectors, and ElevenLabs/Daytona readiness. Staff assistant is the central staff-to-Remi workspace with a transcript, task context, and a sample next-week schedule proposal. Its context panel reads the selected profile’s role-permitted MCP tools from the backend, distinguishes assistant-connected reads from other MCP workflows, and reports when access cannot be checked. A Manager profile can manually approve the proposal; that approval changes only local demo state and does not write to 7shifts. Guest calls remain separate for server-to-guest interactions. Menu & availability, Insights, Settings, and Help center each have their own page. The sidebar stays fixed while the main content area scrolls.

The Menu & availability page reads menu prices from the mock POS through the selected demo account; availability is not checked on that page. It shows generalized category SVG icons from the shared `../../public/menu/` directory. Items in the same category reuse the same icon; the set covers entrees, appetizers, sides, salads, drinks, and desserts. The same shared public directory contains the Remi logo used in the title bar and sign-in page.

The Overview reads `GET /health/dependencies` from the agent API. Agent and mock integration availability are checked live. ElevenLabs and Daytona are labeled as unconfigured or credentials-present-but-unverified; credentials are never returned by the health response. The Settings modal has Connections, Voice agent, Daytona, Agent instructions, Workplace instructions, and Staff access sections. A dedicated Management page appears for Manager, Shift Lead, and Head Chef profiles, showing the workplace staff roster and each person's configured access. The Manager profile can configure each other demo staff profile's enabled state, assistant workflows, and individual MCP tools; selections persist in the desktop profile's local storage. Elevated non-manager profiles have read-only access to the roster in this prototype. These are local demo controls only: no authenticated settings API or backend permission enforcement is connected, and they do not alter the MCP server's fixed role checks. The session greeting uses `POST /voice/greeting` through Electron IPC, keeping provider credentials on the backend. An active staff session starts continuous microphone listening; typed requests go to `POST /agent/turn`, and recognized turns go to `POST /voice/reply`, which runs the agent turn and synthesizes its response through ElevenLabs TTS. Spoken microphone-stop requests require a separate “confirm stop” utterance; pressing the microphone button stops immediately. While ElevenLabs audio is playing, staff can interrupt only with a wake phrase such as “Remi, stop” or “Remi, wait”; other speech is ignored during playback. Microphone audio is segmented locally and sent to the backend for ElevenLabs transcription. During playback, captured utterances are checked for the interruption phrase after ElevenLabs transcription; background noise and transcription latency can affect detection. The Insights page can launch a manager-only background task that reads current mock MarketMan inventory and illustrative YTD receiving data, then analyzes it in an ephemeral Daytona sandbox. The report is returned to the manager for review; no purchase order is created. Daytona task data is held in API process memory, so it is lost if the service restarts. Voice/personality selections and instruction editors remain demo-local and are not applied to agent prompts.

## Development

Requires Node.js 20 or newer and npm.

```bash
npm install
npm start
```

If npm reports that Electron's install script was blocked, approve that dependency and download its desktop runtime before starting:

```bash
npm install-scripts approve electron
npm rebuild electron
npm start
```

`npm start` launches Vite and Electron. Run the FastAPI agent in another terminal to show the connected status:

```bash
cd ../..
uv run --env-file .env uvicorn agent.main:app --app-dir services/agent --reload --port 8000
```

Without the agent, the UI remains usable and reports the service as offline. The microphone button captures speech with Electron media APIs. Microphone permissions depend on the operating system; ElevenLabs credentials and network access are required for transcription and speech playback. Starting a staff session shows “What should we do today {{role}}, {{user}}?” in the transcript and plays it through ElevenLabs when configured. The voice reply endpoint runs the agent graph, using an optional configured LLM or deterministic demo responses. Recognized menu, working staff, today’s shifts, and inventory requests use the MCP server’s validated read functions under the selected demo account. Managers can ask the model to prepare an SMS alert, review the destination and complete message, and say “confirm send” or “cancel alert”. Resend uses email-to-carrier gateways and cannot confirm phone delivery. Other voice mutations and persistent history are not connected.

## Build installers

Run the packaging command on the target platform:

```bash
npm run package:mac
npm run package:win
npm run package:linux
```

electron-builder creates platform-native output under `release/`. macOS distribution outside local development will require signing and notarization configuration.

The platform icons are `assets/icons/remi.icns` for macOS, `assets/icons/remi.ico` for Windows, and size-specific PNGs in `assets/icons/linux/`.

Desktop profiles select mock account IDs; the backend checks the mock directory for the account role and status. Profile selection is not authentication and is intended only for the local demo. The standalone stdio MCP server continues to use `REMI_MCP_ACCOUNT_ID`.
