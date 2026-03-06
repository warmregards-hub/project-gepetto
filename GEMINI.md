# Gemini Configuration — Warm Regards Creative Hub

## Primary Instructions

Read and follow the AGENTS.md file in this project root. It contains the
complete specification for this application. All architecture decisions,
tech stack choices, file structures, API integrations, and build phases
are defined there.

## Key Rules

- Follow AGENTS.md as the single source of truth
- Use React 19 (NOT 18), TypeScript strict, Vite 6, Tailwind CSS 4
- Use Python 3.11+ with FastAPI for the backend
- Use PostgreSQL for BOTH dev and production (NOT SQLite)
- Docker Compose for the full stack
- All API calls go through Kie.ai (OpenAI-compatible format)
- Zero custom CSS — Tailwind utility classes only
- Mobile-first responsive design
- Dark mode default with warm coral accent (#E8825A)

## Build Order

Follow the phases defined in AGENTS.md:
1. Phase 1: Core structure + agent brain
2. Phase 2: Autonomous execution
3. Phase 3: n8n + voice integration
4. Phase 4: Studio Mode
5. Phase 5: Polish + deploy

Start with Phase 1 and Phase 2 together. Show the project structure
and get it running locally via Docker Compose before moving on.
