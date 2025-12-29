"""
Configuration settings for AI Pipeline Service
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Service
    service_name: str = "mdx-ai-pipeline"
    environment: str = "development"
    debug: bool = True
    
    # AssemblyAI
    assemblyai_api_key: str = ""
    
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4"
    azure_openai_api_version: str = "2024-02-15-preview"
    
    # Alternative: OpenAI Direct
    openai_api_key: str = ""
    
    # Azure Service Bus
    azure_servicebus_connection_string: str = ""
    transcription_queue: str = "mdx-transcription-queue"
    notes_queue: str = "mdx-clinical-notes-queue"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    
    # Backend Service
    backend_url: str = "http://localhost:8080"
    
    # Database
    database_url: str = "postgresql+asyncpg://mdx:mdx_secret@localhost:5432/mdxvision"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
