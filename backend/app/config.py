"""Application settings, loaded from environment variables.

The same codebase runs locally, in staging, and on Cloud Run. Only the
environment variables change between them.
"""

from __future__ import annotations

import dataclasses
import os


@dataclasses.dataclass(frozen=True)
class Settings:
    """Runtime configuration.

    Attributes:
        app_name: Service name exposed in health and info responses.
        environment: Deployment environment label (local, staging, prod).
        database_url: PostgreSQL connection string (optional in skeleton).
        clerk_secret_key: Clerk key used to verify session tokens.
        llm_provider: Provider key (``vertex`` for Vertex AI Gemini).
        llm_api_key: Unused for Vertex (ADC). Kept for other vendors.
        llm_model: Vertex Gemini model id.
        gcp_project: GCP project used by Vertex AI.
        gcp_location: Vertex AI region.
        cors_origins: Comma-separated allowed CORS origins.
    """

    app_name: str
    environment: str
    database_url: str
    clerk_secret_key: str
    llm_provider: str
    llm_api_key: str
    llm_model: str
    gcp_project: str
    gcp_location: str
    cors_origins: tuple[str, ...]


def load_settings() -> Settings:
    """Reads settings from environment variables.

    Missing optional values default to empty strings so the skeleton can
    boot on Cloud Run before secrets are wired. Domain endpoints that need
    them should fail closed when values are absent.

    Returns:
        The populated Settings.
    """
    origins_raw = os.getenv('CORS_ORIGINS', 'http://localhost:5173')
    origins = tuple(
        origin.strip()
        for origin in origins_raw.split(',')
        if origin.strip()
    )
    return Settings(
        app_name=os.getenv('APP_NAME', 'coursecompass-api'),
        environment=os.getenv('APP_ENV', 'local'),
        database_url=os.getenv('DATABASE_URL', ''),
        clerk_secret_key=os.getenv('CLERK_SECRET_KEY', ''),
        llm_provider=os.getenv('LLM_PROVIDER', ''),
        llm_api_key=os.getenv('LLM_API_KEY', ''),
        llm_model=os.getenv('LLM_MODEL', 'gemini-2.5-flash'),
        gcp_project=os.getenv(
            'GCP_PROJECT_ID',
            os.getenv('GOOGLE_CLOUD_PROJECT', ''),
        ),
        gcp_location=os.getenv('GCP_LOCATION', 'us-central1'),
        cors_origins=origins,
    )
