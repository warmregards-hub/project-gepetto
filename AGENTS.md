# AGENTS.md — Warm Regards Creative Hub

> Autonomous AI creative operations platform for Warm Regards Studios.
> Built by Callum. Replaces manual tools with a single agentic system
> that generates images, videos, runs QC, organises delivery, and learns.

---

## 1 · Project overview

| Field | Value |
|---|---|
| Name | Warm Regards Creative Hub |
| Owner | Warm Regards Studios Pty Ltd |
| Operator | Solo (Callum) |
| Monthly volume | 100-200 images, 40-50 videos |
| Active clients | Drew (5TRIPS / BaySmokes), Betway F1 |
| Domain | ai.warmregards.studio |

### What this system does

User speaks or types a brief. The agent autonomously:
1. Plans the creative (concepts, shot list, model selection)
2. Generates exactly the number of assets requested via Kie.ai APIs (uses webhooks in prod, polling fallback in dev)
3. Presents ALL generated assets to user in a 2-column gallery
4. User reviews: KEEP or REJECT each image
5. Rejected slots are regenerated with adjusted prompts based on keep/reject patterns
6. Loops until all slots are filled with kept assets
7. Saves kept assets to local storage with download links
8. Triggers existing n8n workflows for video/audio pipelines
9. Reports results with cost summary
10. Learns preferences for next time (decisions logged to qc-feedback.jsonl, distilled into learned-patterns.json)

**Zero manual steps between brief and delivery (other than KEEP/REJECT review).**

### Two interfaces

**Agent Mode (primary):** Chat interface. Voice or text input. Full autonomous execution.
**Studio Mode (secondary):** Manual generation panel. Pick model, write prompt, generate one thing.

---

## 2 · Tech stack (validated March 2026)

### Frontend
- **React 19.2** (NOT 18)
- TypeScript 5.x strict mode
- Vite 6.x
- Tailwind CSS 4.x — zero custom CSS files
- Zustand (state management)
- TanStack Query (server state + caching)
- ElevenLabs React SDK (@11labs/react)

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy 2.x async
- httpx (async HTTP client)
- WebSockets (real-time status)
- Pydantic v2 (schemas)
- python-jose (JWT auth)
- bcrypt (password hashing)

### Database
- PostgreSQL via Docker (dev AND production — NOT SQLite)

### Infrastructure
- Docker + Docker Compose
- Nginx reverse proxy (production)
- Let's Encrypt SSL (production)

### External APIs
| Service | Purpose | Format |
|---|---|---|
| Kie.ai | Gemini 2.5 Flash brain + image/video gen (webhooks) | OpenAI-compatible |
| ElevenLabs | Voice I/O | WebRTC + REST |
| Local Storage | File download via app UI | Local filesystem |
| n8n Cloud | Trigger existing workflows | Webhooks (POST) |
| Webhook Callback | Receive generation results | POST `/api/kie/callback` |

---

## 3 · Project structure

```
warm-regards-creative-hub/
├── AGENTS.md
├── GEMINI.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── Dockerfile
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css (Tailwind directives only)
│       ├── stores/
│       │   ├── agentStore.ts
│       │   ├── projectStore.ts
│       │   └── costStore.ts
│       ├── hooks/
│       │   ├── useAgent.ts
│       │   ├── useVoice.ts
│       │   └── useWebSocket.ts
│       ├── components/
│       │   ├── agent/
│       │   │   ├── ConversationView.tsx
│       │   │   ├── VoiceInput.tsx
│       │   │   ├── ScriptPaste.tsx
│       │   │   ├── ProjectSelector.tsx
│       │   │   └── StatusMonitor.tsx
│       │   ├── studio/
│       │   │   ├── ImageGenerator.tsx
│       │   │   ├── VideoGenerator.tsx
│       │   │   ├── Gallery.tsx
│       │   │   └── BatchProcessor.tsx
│       │   └── shared/
│       │       ├── CostTracker.tsx
│       │       ├── Layout.tsx
│       │       └── LoadingStates.tsx
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── AgentPage.tsx
│       │   └── StudioPage.tsx
│       ├── lib/
│       │   ├── api.ts
│       │   └── constants.ts
│       └── types/
│           └── index.ts
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── agent.py
│       │       ├── generate.py
│       │       ├── projects.py
│       │       ├── n8n.py
│       │       ├── learning.py
│       │       └── auth.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── claude_agent.py
│       │   ├── kie_client.py
│       │   ├── vision_qc.py
│       │   ├── n8n_client.py
│       │   ├── storage_service.py
│       │   ├── elevenlabs_client.py
│       │   ├── learning_engine.py
│       │   └── cost_tracker.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── generation.py
│       │   ├── project.py
│       │   ├── conversation.py
│       │   └── preference.py
│       └── schemas/
│           ├── __init__.py
│           ├── agent.py
│           ├── generation.py
│           └── project.py
└── projects/
    ├── drew-5trips/
    │   ├── preferences.md
    │   ├── successful-prompts.json
    │   ├── qc-standards.json
    │   └── assets/              ← product images, logos, reference material
    └── betway-f1/
        ├── preferences.md
        ├── successful-prompts.json
        ├── qc-standards.json
        └── assets/              ← product images, logos, reference material
```

---

## 4 · Critical rules

### UX rules
- Mobile-first responsive design
- Dark mode default, warm coral accent (#E8825A)
- Loading states for everything — no blank screens
- Real-time status via WebSocket for all jobs
- Toast notifications for completions
- Cost tracker ALWAYS visible

### Agent behaviour rules
- NEVER ask for confirmation mid-workflow — execute fully then report
- GENERATE EXACTLY the amount requested (e.g., 10 selfies = 10 images generated). Do not pad variants.
- ALL images go to a review gallery immediately
- Human is the sole QC. Rejected slots are regenerated with tweaked prompts based on kept feedback.
- ALWAYS use the model the user specifies in their brief — do NOT auto-select models
- If user does not specify a model, ASK which model to use before generating
- ALWAYS check global AND project preferences AND learned-patterns.json before generating
- ALWAYS log costs per request
- ALWAYS retry failed generations (max 3 attempts)
- NO automated QC scoring out of the box. vision_qc_enabled: false by default.
- UGC content = ALWAYS 9:16 aspect ratio
- Product shots = 1:1, Cinematic = 16:9

### Code quality rules
- TypeScript strict mode — no any types
- All API responses typed with Pydantic schemas
- Async error handling with retries everywhere
- Environment variables for ALL secrets
- Structured JSON logging
- Database migrations via Alembic

### Security rules
- Login required for all routes (JWT tokens)
- Rate limiting: 100 API calls/hour
- Cost hard limits: $5/session, $150/month (configurable via env)
- HTTPS only in production
- CORS restricted to frontend origin
- No secrets in Git

---

## 5 · Core agent workflow

### The brain: claude_agent.py

Central orchestrator. Receives user messages, autonomously executes multi-step creative workflows. Uses Claude Sonnet 4.5 via Kie.ai with tool/function calling.

### Pivot: Agentic conversation first

- Default behavior is collaborative brief-building and planning.
- Tool calls are only made when the user explicitly requests generation or confirms they are ready.
- Model selection is only requested during generation intent, never during normal conversation.
- Mock mode: LLM chat remains live; only image/video generation is mocked. Toggleable at runtime via UI.
- If the user is vague about model choice ("anything" / "whatever"), pick the default model from global/project preferences or learned patterns without overriding explicit user choices.
- If the user asks for an image intended for video use (e.g. "start frame for a video"), treat it as an image request unless they explicitly ask to generate a video clip.
- The agent must use `search_available_models` to resolve exact model API names and ask the user to clarify when ambiguous.
- Tool loop safety: max 20 tool calls per user turn. If reached, stop and report what completed so far.
- Error UX rule: never expose raw upstream API errors to user-facing chat.

### Agent tools (8 total)

**search_available_models** — params: optional query, kind (image/video/chat/any). Returns available models with API names and metadata. This tool MUST be used to find valid models when they are not explicitly known from preferences or user instruction.

**generate_images** — params: prompts (array of strings), model (string, exact API name), project_id, optional style_overrides object. Generates exact count of prompts provided. Includes `callBackUrl` in post request. The tool is DUMB; it does not hardcode, validate, or branch based on the model.

**generate_videos** — params: prompts (array), model (string, exact API name), optional reference_images (array of URLs), project_id. Includes `callBackUrl` in post request. The tool is DUMB; it does not hardcode, validate, or branch based on the model.

~~**run_vision_qc**~~ — REMOVED from active tools for now. Kept disabled in codebase. When `vision_qc_enabled` is true (after 100+ feedbacks), it pre-rejects obvious failures.

**save_to_storage** — params: files (array of URLs/paths), project_id, subfolder string. Naming: /storage/[client]/[date]_[campaign]/[type]/

**trigger_n8n_workflow** — params: workflow_name (enum: ugc-batch, video-render, script-process, voice-generate), payload object.

**read_project_preferences** — params: project_id. Returns preferences.md, successful-prompts.json, qc-standards.json content.

**update_project_preferences** — params: project_id, updates object. Merges into existing preference files.

**log_cost** — params: amount_usd (number), service (enum: kie-chat, kie-image, kie-video, kie-vision, elevenlabs), model string, project_id, description string.

### Tool definitions format

All tools use OpenAI function calling format:
```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "description": "...",
    "parameters": {
      "type": "object",
      "properties": { ... },
      "required": [...]
    }
  }
}
```

### Example autonomous workflow

User: "Generate 50 gym UGC frames for the 5TRIPS campaign"

Agent executes (zero user interaction):
1. read_project_preferences("drew-5trips") — loads style, models, QC threshold
2. Plans 50 concepts (30 face testimonials, 20 environment shots)
3. generate_images(100 prompts, gpt-image-1) — 50 concepts x 2 variants
4. run_vision_qc(100 images) — scores all, finds 8 below threshold
5. generate_images(8 retry prompts with tweaks) — regenerates failures
6. run_vision_qc(8 new) — 7/8 pass, 1 skipped
7. Selects best variant per concept (50 finals from ~108 generated)
8. save_to_storage(50 files, "drew-5trips", "2026-03-04_Gym-UGC")
9. log_cost($3.24 images + $0.85 QC)
10. update_project_preferences(avg_qc=8.2, top_prompts, retry_rate=0.08)
11. Reports: 50 frames, 92% first-pass, $4.09, download link, 6m42s

---

## 6 · Kie.ai integration (verified March 2026)

### Configuration
- Base URL: https://api.kie.ai/v1
- Format: OpenAI-compatible (all endpoints)
- Auth: Bearer token via KIE_API_KEY header

### Available models

**Chat (agent brain):** claude-sonnet-4-5 (supports tool calling)

**Image generation:**
| Model | Best for | Cost |
|---|---|---|
| gpt-image-1 | Faces, people, UGC | ~$0.03/image |
| nano-banana-pro | Cheap bulk, environments | ~$0.02-0.12/image |
| midjourney | Stylised, artistic | Varies |
| flux-kontext | Text-in-image, brand | Varies |

**Video generation:**
| Model | Best for | Cost |
|---|---|---|
| veo-3.1-fast | Quick drafts | ~$0.30-0.40/clip |
| veo-3.1 | Quality renders | ~$2.00/8sec |
| kling | Character animation | Varies |
| sora2 | Cinematic, narrative | Varies |
| runway-aleph | Latest Runway model | Varies |

**WRONG model names (do NOT use):**
- ~~DALL-E 3~~ use gpt-image-1
- ~~Veo 3~~ use veo-3.1 or veo-3.1-fast
- ~~Runway Gen-3~~ use runway-aleph

### API patterns

Chat completions: `POST /v1/chat/completions` with messages, tools, tool_choice (model defined in paylaod)
Image/Video generation (WEBHOOK): `POST /v1/images/generations` (or `/v1/videos/generations`) with `callBackUrl` and `model` in payload → Kie.ai POSTs result to our backend `POST /api/kie/callback` when done.
*Fallback for dev mode*: If localhost, omit `callBackUrl`, returns `task_id` → poll `GET /v1/task/{task_id}` every 3s until status=succeeded.

### Reliability
- Retry 3x with exponential backoff (1s, 3s, 9s)
- Model fallback on 3x consecutive failure
- Log all failures for tracking
- ~80% reliability on some models
- Image generation polls up to 120s (40 attempts × 3s)
- Endpoint self-healing: successful endpoint/model combos are written to `endpoint_registry.json` and preferred on future runs.
- Generation transport: use `callBackUrl` webhooks in non-development environments; use polling fallback only in development/local.

### Image serving
- Real mode: images served via `/api/storage/proxy?url=...` — backend proxies authenticated CDN URLs
- No auth required on `/api/storage/download/` — browser img tags cannot send JWT headers

### Mock mode (MOCK_GENERATION=true)
When MOCK_GENERATION env var is true:
- generate_images bypasses Kie.ai entirely, serves `car.png` from `/storage/car.png` as placeholder
- All 4 variants are the same placeholder image
- Agent brain (Claude chat via Kie.ai) still works normally
- Cost tracker logs $0.00 for all mock generations
- All other tools work as normal
- This is the DEFAULT for development — set MOCK_GENERATION=false when ready to spend real money

---

## 7 · Learning system

### Preference hierarchy (two layers)
1. **Global** (`/projects/global/preferences.md`) — applies to ALL projects. Defines aspect ratios, UGC rules, generation defaults.
2. **Per-project** (`/projects/[id]/preferences.md`) — overrides global where specified. (Can enable `vision_qc_enabled: true` in the future).

### Learning Data
- `qc-feedback.jsonl` — Raw append-only logs of every review: prompt, model, KEEP/REJECT.
- `learned-patterns.json` — Compact, distilled summary of insights: `positive_patterns`, `negative_patterns`, `keep_rate_by_model`, `recommended_prompt_additions`, `recommended_prompt_exclusions`.

### Human review & Learning loop
1. Generated variants shown in 2-column 9:16 gallery in the chat UI
2. KEEP / REJECT logged to `qc-feedback.jsonl`
3. After batch completes, Learning Engine analyzes patterns from feedback and updates `learned-patterns.json`
4. Every 5 sessions, rebuilds patterns entirely from historic feedback
5. Agent MUST incorporate learned additions/exclusions automatically.
6. Agent tells user if it notices a pattern shift.
7. Rejected slots are regenerated immediately with tweaked prompts based on these learning loops.

---

## 8 · n8n integration

Pattern: Agent triggers existing n8n workflows via webhook POST, n8n calls back when done.

### n8n webhook endpoints
- ugc-batch: {N8N_BASE}/webhook/ugc-batch
- video-render: {N8N_BASE}/webhook/video-render
- script-process: {N8N_BASE}/webhook/script-process
- voice-generate: {N8N_BASE}/webhook/voice-generate

### Outbound payload
job_id, project_id, callback_url (https://ai.warmregards.studio/api/n8n/callback), images array, scripts array, voice_id, metadata object (batch_name, style, output_format, resolution).

### Callback (Creative Hub receives)
POST /api/n8n/callback with job_id, status (completed/failed/partial), outputs array, errors array, processing_time_seconds.

---

## 9 · Voice interface

Voice mode: ElevenLabs React SDK, useConversation() hook, push-to-talk (saves credits), Lora voice clone for output, user real voice for input via STT.

Text mode: Standard input + paste support for long scripts + drag-drop .txt/.md.

Hybrid: Voice instructions + pasted scripts in same conversation.

---

## 10 · Cost tracking

### Live display
Session: $X | Month: $X/$150 | [Project]: $X (N assets)

### Schema
CostEntry: id, timestamp, project_id, service, model, amount_usd, description, job_id.

### Controls
- Session limit: $5 (COST_LIMIT_SESSION env var)
- Monthly limit: $150 (COST_LIMIT_MONTHLY env var)
- Warning at 80%
- Agent stops if limit exceeded

---

## 11 · Local file storage

/storage/[client]/[date]_[campaign-name]/images/ + /videos/ + metadata.json
All files served via the app with download buttons. Downloadable individually or as ZIP.

**Storage mount:** `./storage` on host → `/storage` in container (bind mount, not Docker volume).
Drop any file into `projectgepetto/storage/` and it's immediately accessible inside the container.
`car.png` in the root of `./storage` is used as the mock image placeholder.

---

## 12 · Environment variables

KIE_API_KEY, KIE_BASE_URL (https://api.kie.ai/v1), ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_VOICE_ID, N8N_WEBHOOK_BASE_URL, DATABASE_URL (postgresql+asyncpg://hub:password@db:5432/creative_hub), POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, ENVIRONMENT, SECRET_KEY, FRONTEND_URL, BACKEND_URL, COST_LIMIT_SESSION (5.00), COST_LIMIT_MONTHLY (150.00), ADMIN_USERNAME, ADMIN_PASSWORD_HASH, STORAGE_PATH (/storage — Docker volume mounted for persistence), MOCK_GENERATION (true/false — when true, image and video generation returns placeholder files instead of calling Kie.ai, so you can test the full workflow without spending money. Agent brain chat still works normally. Set to false when ready to generate real assets).

---

## 13 · Build phases

### Phase 1 — Core structure + agent brain (Week 1)
- Full project scaffolding (all folders + configs)
- docker-compose.yml (frontend + backend + PostgreSQL)
- Database models + Alembic migrations
- FastAPI app with all route stubs
- JWT auth (login, tokens, protected routes)
- Claude agent service via Kie.ai (tool calling loop)
- Kie.ai client (chat completions)
- Cost tracking service
- WebSocket for real-time updates
- React app shell (dark mode, routing, layout)
- ConversationView, VoiceInput stub, ScriptPaste, ProjectSelector
- StatusMonitor, CostTracker components

### Phase 2 — Autonomous execution (Week 2)
- Kie.ai image gen with retry + fallback
- Kie.ai video gen with retry + fallback
- Vision QC (Claude vision scoring)
- Auto-regeneration loop
- Local storage service (folders, upload, links)
- Learning engine (read/write preferences)
- Full autonomous workflow (brief to delivery)
- WebSocket progress streaming

### Phase 3 — n8n + voice (Week 2-3)
- n8n webhook trigger client
- n8n callback endpoint
- ElevenLabs voice (React SDK)
- Voice input, transcription, agent processing
- Agent response, Lora TTS, audio output

### Phase 4 — Studio Mode (Week 3-4)
- Manual image gen panel
- Manual video gen panel
- Asset gallery
- Batch processor

### Phase 5 — Deploy (Week 4)
- Production docker-compose (Nginx, SSL)
- VPS deployment scripts
- Production env config
- Smoke tests

---

## 14 · Success metrics

| Metric | Target |
|---|---|
| Time per batch | 90% reduction |
| QC pass rate | 90%+ first-pass |
| Monthly cost | $65-80 total |
| Delivery speed | < 15 min for 50 images |

---

## 15 · Constraints

- Never exceed cost limits without explicit override
- Never delete from storage (only add)
- Never modify n8n workflows (only trigger via webhooks)
- Log everything (every API call, cost, QC result)
- Graceful degradation when Kie.ai is down
- Max 10 concurrent Kie.ai calls, 100/minute
- All content stored locally + Drive (dual backup)
