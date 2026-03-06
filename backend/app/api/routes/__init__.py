from .agent import router as agent_router
from .generate import router as generate_router
from .projects import router as projects_router
from .n8n import router as n8n_router
from .learning import router as learning_router
from .auth import router as auth_router
from .storage import router as storage_router

__all__ = ["agent_router", "generate_router", "projects_router", "n8n_router", "learning_router", "auth_router", "storage_router"]
