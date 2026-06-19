from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Azure AI Foundry (Unified AI Platform)
    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT: str
    AZURE_AI_FOUNDRY_PROJECT_API_KEY: str

    # OpenAI (for embeddings)
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # Supabase (PostgreSQL + Vector DB)
    DATABASE_URL: str
    DIRECT_URL: str
    ALEMBIC_URL: str

    # Supabase Storage
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_RESUME_BUCKET: str = "resumes"
    
    # Message history limit for context
    MESSAGE_HISTORY_LIMIT: int = 8
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
