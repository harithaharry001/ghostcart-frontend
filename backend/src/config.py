"""
GhostCart Configuration Module

Loads environment variables for backend configuration following AP2 protocol requirements.
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    AP2 Compliance Notes:
    - All secrets for HMAC signatures are environment-based
    - AWS region configurable for Bedrock access
    - Demo mode enables accelerated monitoring for hackathon demonstration
    """

    # AWS Bedrock Configuration
    aws_region: str = "us-east-1"  # Configurable via AWS_REGION environment variable
    aws_bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"

    # Demo Configuration
    demo_mode: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Cryptographic Secrets (HMAC-SHA256 for demo)
    user_signature_secret: str = "user_secret_key_demo_only_change_me"
    agent_signature_secret: str = "agent_secret_key_demo_only_change_me"
    payment_agent_secret: str = "payment_secret_key_demo_only_change_me"

    # Database
    database_path: str = "./ghostcart.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
