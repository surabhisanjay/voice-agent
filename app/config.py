"""
Configuration management for the Inbound Agent.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"

    # Database Configuration
    database_url: str = "sqlite:///./inbound_agent.db"

    # Vector Store Configuration
    vector_store_path: str = "./chroma_db"

    # Document Configuration
    document_path: str = "./data"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Embedding model configuration
    embedding_model: str = "llama3.2"

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "./logs/inbound_agent.log"

    # Agent Configuration
    escalation_confidence_threshold: float = 0.5
    max_conversation_history: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
