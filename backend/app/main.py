from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import agent, generate, projects, n8n, learning, auth, storage, kie, sessions, lora

app = FastAPI(title="Warm Regards Creative Hub (Project Gepetto)")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(n8n.router, prefix="/api/n8n", tags=["n8n"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(storage.router, prefix="/api/storage", tags=["storage"])
app.include_router(kie.router, prefix="/api/kie", tags=["kie"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(lora.router, prefix="/api/lora", tags=["lora"])


@app.on_event("startup")
async def startup_event():
    from app.services.kie_client import KieClient
    KieClient.initialize_registry()

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": "Gepetto"}
