# Voice Agent Latency Estimates

**Project:** Remi restaurant voice-agent backend  
**Context:** SDxSDSU Hackathon  
**Updated:** 2026-11-08

This document separates published ElevenLabs component measurements from planning estimates for Remi. Published provider measurements are not guarantees of end-to-end latency: network, user turn detection, application processing, POS calls, and audio playback all affect what a caller experiences.

**MVP context:** Remi currently targets one Python FastAPI service with LangGraph/LangChain agent orchestration, ElevenLabs for planned speech integration, and mock POS endpoints with seeded data. The ranges below are planning assumptions until measured in Remi. Mock POS measurements do not predict latency against a live POS vendor. Daytona is optional for isolated execution and is not assumed in the ordinary POS request path.

## ElevenLabs published measurements

ElevenLabs' latency methodology describes these as medians (p50) measured on production traffic. TTS figures use WebSocket streaming with warm voices and measure server-side time from request receipt to first audio returned.

| Component | Published median | Measurement |
|---|---:|---|
| Scribe v2 Realtime STT | ~150 ms | Time to committed transcript; partial transcripts are available during speech |
| Eleven Flash v2.5 TTS | ~100 ms | Server-side time to first audio |
| Eleven v4 Turbo TTS | ~100 ms | Server-side time to first audio |
| Eleven v3 Conversational TTS | ~165 ms | Server-side time to first audio |
| ElevenAgents orchestration | <100 ms overhead | ElevenLabs-published orchestration overhead |
| ElevenAgents end-to-end | ~150 ms median reported | Request-to-audible-speech figure reported by ElevenLabs for v4 Turbo |

The figures exclude network round trips and, for TTS component measurements, upstream application work and client playback buffering. The Agents end-to-end figure is a provider-reported reference point and is not a guarantee for Remi.

## Remi planning estimate

Assumptions:

- Caller audio arrives over a persistent streaming connection.
- STT returns partial results while the caller is speaking.
- The agent uses a low-latency LLM and begins streaming once it has a usable phrase.
- TTS audio is streamed to the client instead of waiting for a complete audio file.
- The caller and service regions are reasonably close to the relevant provider endpoints.

| Stage | Planning range | Notes |
|---|---:|---|
| End-of-turn detection | 250–600 ms | Depends on silence threshold and turn-taking behavior |
| STT finalization | 100–250 ms | Partial transcription can occur before the turn ends |
| LLM time to first useful response | 200–800 ms | Highly dependent on model, prompt size, context, and reasoning settings |
| Agent, API, and network overhead | 50–200 ms | Includes application processing and provider round trips |
| TTS to first client audio | 150–350 ms | Includes provider and network time; assumes streaming |
| **Stop-speaking to first audio** | **~0.8–2.2 s** | Planning range; stages may overlap |

These ranges are an engineering estimate, not measurements from a deployed Remi system. Components can overlap: STT streams partials, and LLM output can feed TTS before the full response is complete. Therefore, adding every row as if strictly sequential would overstate expected latency.

A useful initial product target is **under 1 second p50 and under 1.5 seconds p95** for ordinary conversational responses. Measure actual Remi traffic before treating these targets as achieved.

## POS action path

The single Python FastAPI service invokes the POS adapter directly, avoiding an extra internal application-service hop. In the MVP that adapter should use the mock POS API. This measures Remi's local action path, not vendor network/API latency.

For a turn that needs a POS lookup or write:

- A fast lookup may add tens to hundreds of milliseconds.
- Order submission, inventory, or other external operations may take longer and vary with the vendor and environment.
- If the agent waits for the POS result before speaking, use **~1.2–3 seconds** as an initial planning range from caller stop to first audio.
- To reduce perceived silence, the agent can stream a brief acknowledgement while the POS request runs, then speak the result. The acknowledgement must not imply success before the POS confirms it.

## Mock integration benchmarks and simulation profiles

Remi includes a configurable mock server (`services/mocks`) simulating Oracle POS, 7shifts (labor/scheduling), and MarketMan (inventory/recipes) with realistic jitter and synthetic latency profiles:

- **`low_latency`** (15–45ms Oracle, 30–70ms 7shifts, 40–90ms MarketMan): Simulates an on-premise edge setup or high-performance LAN workstation.
- **`typical_cloud`** (60–140ms Oracle, 90–180ms 7shifts, 100–220ms MarketMan): Standard cloud SaaS multi-vendor environment over broadband.
- **`rush_hour_degraded`** (180–450ms Oracle, 250–600ms 7shifts, 300–800ms MarketMan + 2–5% error rate): Stress test for rush periods, congested Wi-Fi, or upstream vendor throttling.

Restaurants or benchmark runners can also specify custom exact latency bounds via environment variables (`ORACLE_POS_MIN_LATENCY_MS`, `MARKETMAN_MIN_LATENCY_MS`, etc.).

Successful decorated routes that return dictionaries include `_debug_latency_ms` and `_simulated_vendor` fields. These fields are not response headers and are not included on simulated failures or non-dictionary responses. Delays are randomized, and the degraded profile injects random failures; benchmark runs are therefore not fully deterministic.

## Likely latency drivers

1. **Turn-end detection:** waiting too long after the caller stops can add hundreds of milliseconds to every turn.
2. **LLM first-token time:** model choice, prompt/context size, and reasoning effort affect how soon a useful response can start.
3. **POS response time:** external restaurant systems can vary and may dominate action turns.
4. **Streaming and buffering:** batch transcription or waiting for a complete TTS file adds avoidable delay.
5. **Geography and connection setup:** placing services near users/providers and reusing persistent connections can reduce round trips.

FastAPI's framework overhead is expected to be a small part of this pipeline compared with model inference and external provider calls; validate that assumption with route-level measurements.

## Measurement plan

Record timestamps for these events, using a shared trace or conversation ID:

- First audio packet received
- Caller turn end detected
- STT committed transcript received
- LLM request sent and first useful token received
- POS request sent and response received, when applicable
- TTS request sent and first audio chunk received
- First audio chunk played to the caller, when client telemetry is available

Report p50 and p95 separately for ordinary responses and POS action turns. Also track turn-end detection delay, time to first audio, total response duration, POS latency, failures, and interruptions. Compare runs from the same client region and with the same audio format, voice, and prompt.

## Architecture choice

**ElevenAgents** provides managed STT, LLM, TTS, and turn-taking orchestration, reducing the work needed to reach a conversational prototype. Remi's current planned architecture instead uses LangGraph/LangChain orchestration in the FastAPI service with ElevenLabs speech APIs. A custom pipeline gives Remi more control over each stage but makes Remi responsible for streaming, endpointing, retries, cancellation, and observability. The ElevenAgents figures above are a comparison reference and are not a direct prediction for this custom pipeline.

Keep POS operations behind validated, narrowly scoped FastAPI endpoints and provider adapters in the same service. Benchmark the full flow before making framework-level latency decisions.

## Sources

- [ElevenLabs latency methodology](https://elevenlabs.io/docs/eleven-api/concepts/latency-methodology)
- [ElevenLabs latency explanation](https://elevenlabs.io/docs/eleven-api/concepts/latency)
- [ElevenLabs voice-agent latency optimization](https://elevenlabs.io/blog/voice-agent-latency-optimization)
- [ElevenLabs orchestration engine](https://elevenlabs.io/blog/unpacking-elevenagents-orchestration-engine)
- [ElevenLabs conversation flow and turn-taking settings](https://elevenlabs.io/docs/eleven-agents/customization/conversation-flow)
