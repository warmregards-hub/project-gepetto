# Implementation Plan Updates

## Pivot: Agentic Conversation First

### Why
- The agent should behave like a planning partner, not a trigger-happy generator.
- Users must be able to hold a long planning session and only generate when ready.

### Behavioral Changes
- Default mode is conversational brief-building.
- Tool calls are allowed only when the user explicitly requests generation or confirms readiness.
- Model selection is asked only during generation intent, not during normal conversation.

### Current Implementation Notes
- Generation intent gating added in `backend/app/services/claude_agent.py` using a lightweight heuristic.
- Mock mode now uses live LLM for chat; only image/video generation is mocked in `backend/app/services/kie_client.py`.
- UI toggle added to switch mock/live at runtime via `/api/learning/mock`.
- Chat image gallery now renders in a 2-column grid; landscape assets span both columns.
- Generated filenames now use UUIDs per batch to avoid collisions between messages.
- Generation intent now reuses last requested count and treats "anything" as a default model if asked.
- CORS allows localhost + 127.0.0.1 for dev to prevent blocked API calls.
- Default model selection now uses learned patterns first, then global/project preferences, and only falls back to gpt-image-1/veo-3.1-fast.
- Rebuilt `frontend/src/stores/layoutStore.ts` with ASCII-only content to fix BOM parse error.
- Generation intent expanded to include "get/show/want" phrasing and vague model responses.
- Model resolution now detects "flux" shorthand and reuses the last model from conversation history.
- Generation now clamps output count to the user-requested number, defaulting to 1 when unspecified.
- Follow-up requests like "more/another/again" now trigger generation using prior context.
- Generation fallback always uses default model if none is detected, preventing empty "What are we making?" loops.
- Explicit generation requests with a model now bypass LLM and call tools directly.
- Explicit model + image requests are now hard-routed to tool calls before any LLM response.
- Direct-tool path now returns explicit errors if generation fails instead of falling back to generic chat responses.
- Kie image generation now retries via generic `/v1/images/generations` if model-specific route returns 404.
- Kie base URL now strips trailing /v1 to avoid double /v1 paths.
- Rebuilt `backend/app/services/kie_client.py` with endpoint pattern retries, fallback models, and structured safe failure outputs.
- Added endpoint self-healing registry persisted at `endpoint_registry.json` (URL/model/params success tracking + failure streaks).
- Agent startup now initializes registry state so known-good endpoints are reused across sessions.
- Rebuilt `backend/app/services/claude_agent.py` tool loop with assistant->tool->assistant iteration (no hardcoded parsing; Claude selects models via tool).
- Added `search_available_models` tool to let Claude resolve model names dynamically from live/cache data.
- Tool loop now enforces "tool call or clarification" when user requests generation.
- Added `MAX_TOOL_CALLS=20` guard per user turn with stop-and-report behavior.
- User-facing errors are now sanitized (no raw upstream stack traces/status dumps in chat).
- Webhook-first transport enforced via `callBackUrl` outside development; polling remains development fallback.
- Asset-kind detection now disambiguates image vs video intent (e.g. "image start frame for video" stays image generation).
- Model parsing now recognizes "nano banana" aliases and maps them to `nano-banana-pro`.
- Tool definitions are now only passed to Claude when generation intent is active, preventing accidental tool calls during planning chat.

### Next Steps
- Refine intent detection to track a session-level "brief draft" state.
- Add a short brief summary and a "ready to generate?" confirmation step before tool calls.
