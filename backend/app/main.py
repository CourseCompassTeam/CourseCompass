"""CourseCompass backend entry point."""

from __future__ import annotations

import os
from datetime import datetime
from datetime import timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from app.api.errors import register_exception_handlers
from app.api.v1 import admin_ingest
from app.api.v1 import query
from app.config import Settings
from app.config import load_settings
from app.orchestration.provider_factory import create_embedding_provider
from app.orchestration.provider_factory import create_llm_provider
from app.repositories.factory import build_tool_dispatcher

_LOG = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Builds the FastAPI application.

    Registers the v1 routers (query, admin ingest), health probes used by
    Cloud Run, and the error handlers that return the standard error
    envelope. When ``LLM_PROVIDER`` is configured, attaches a Vertex AI
    Gemini chat client on ``app.state.llm_provider``. When a GCP project
    is set, attaches ``app.state.embedding_provider`` for syllabus
    vectors.

    Args:
        settings: Optional preloaded settings. When omitted, settings are
            loaded from the environment.

    Returns:
        The configured FastAPI application.
    """
    settings = settings or load_settings()

    application = FastAPI(
        title=settings.app_name,
        version='0.1.0',
        description='CourseCompass advising API',
    )
    application.state.settings = settings
    application.state.llm_provider = None
    application.state.embedding_provider = None
    application.state.tool_dispatcher = None
    if settings.llm_provider:
        try:
            application.state.llm_provider = create_llm_provider(settings)
        except ValueError as exc:
            _LOG.warning('LLM provider not attached: %s', exc)
    if settings.gcp_project and settings.embedding_model:
        try:
            application.state.embedding_provider = (
                create_embedding_provider(settings)
            )
        except ValueError as exc:
            _LOG.warning('Embedding provider not attached: %s', exc)
    if settings.database_url:
        try:
            application.state.tool_dispatcher = build_tool_dispatcher(
                settings.database_url,
                embedding_provider=application.state.embedding_provider,
            )
        except Exception as exc:
            _LOG.warning('Tool dispatcher not attached: %s', exc)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    register_exception_handlers(application)
    application.include_router(query.router)
    application.include_router(admin_ingest.router)

    @application.get('/health')
    def health() -> dict[str, str]:
        """Liveness probe for Cloud Run and local checks."""
        return {'status': 'ok'}

    @application.get('/ready')
    def ready() -> dict[str, str]:
        """Readiness probe. Extend with dependency checks later."""
        return {'status': 'ready'}

    @application.get('/')
    def root() -> dict[str, str]:
        """Minimal root response for smoke tests."""
        return {
            'service': settings.app_name,
            'environment': settings.environment,
            'status': 'running',
        }

    @application.get('/api/info')
    def info() -> dict[str, str]:
        """Runtime metadata helpful when verifying a Cloud Run revision."""
        llm_status = 'configured' if application.state.llm_provider else 'off'
        embed_status = (
            'configured' if application.state.embedding_provider else 'off'
        )
        db_status = (
            'configured' if application.state.tool_dispatcher else 'off'
        )
        return {
            'service': settings.app_name,
            'environment': settings.environment,
            'revision': os.getenv('K_REVISION', 'local'),
            'cloud_service': os.getenv('K_SERVICE', 'local'),
            'llm_provider': settings.llm_provider or 'none',
            'llm_status': llm_status,
            'embedding_model': settings.embedding_model or 'none',
            'embedding_dimensions': str(settings.embedding_dimensions),
            'embedding_status': embed_status,
            'database_status': db_status,
            'time_utc': datetime.now(timezone.utc).isoformat(),
        }

    return application


app = create_app()
