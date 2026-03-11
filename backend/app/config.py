from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App
    environment: str = "development"
    secret_key: str
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    
    # DB
    database_url: str
    
    # external APIs
    kie_api_key: str
    kie_base_url: str = "https://api.kie.ai"
    kie_chat_model: str = "gemini-2.5-flash"
    kie_chat_reasoning: str = "low"
    kie_chat_temperature: float = 0.2
    kie_trace_enabled: bool = True
    kie_trace_path: str = "/app/kie_trace.jsonl"
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_voice_id: str = ""
    n8n_webhook_base_url: str = ""

    # Drive + notifications
    google_service_account_json: str = ""
    google_drive_folder_id: str = ""
    ntfy_base_url: str = "https://ntfy.sh"
    ntfy_topic: str = "WR-ProjectGepetto"
    
    # Operations
    cost_limit_session: float = 5.0
    cost_limit_monthly: float = 150.0
    admin_username: str = "admin"
    admin_password: str = "gepetto"
    storage_path: str = "/storage"
    mock_generation: bool = False
    endpoint_registry_path: str = "/app/endpoint_registry.json"
    model_cache_path: str = "/app/model_cache.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
