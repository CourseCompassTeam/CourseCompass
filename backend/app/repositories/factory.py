"""Wires PostgreSQL repositories to services and MCPTools."""

from __future__ import annotations

from app.embeddings.embedding_provider import EmbeddingProvider
from app.orchestration.tool_dispatcher import ToolDispatcher
from app.repositories.connection import Database
from app.repositories.postgres_audit import PostgresAuditRepository
from app.repositories.postgres_catalog import PostgresCatalogRepository
from app.repositories.postgres_directory import PostgresDirectoryRepository
from app.repositories.postgres_ingestion import PostgresIngestionRepository
from app.repositories.postgres_milestone import PostgresMilestoneRepository
from app.repositories.postgres_schedule import PostgresScheduleRepository
from app.services.audit_service import AuditService
from app.services.campus_directory_service import CampusDirectoryService
from app.services.course_catalog_service import CourseCatalogService
from app.services.student_milestone_service import StudentMilestoneService
from app.tools.mcp_tools import MCPTools


def build_tool_dispatcher(
    database_url: str,
    embedding_provider: EmbeddingProvider | None = None,
) -> ToolDispatcher:
    """Builds the live tool stack against PostgreSQL.

    Args:
        database_url: PostgreSQL connection string.
        embedding_provider: Optional leftover-course ranker.

    Returns:
        A dispatcher ready for POST /api/v1/query.
    """
    database = Database(database_url)
    audit_repo = PostgresAuditRepository(database)
    catalog_repo = PostgresCatalogRepository(database)
    directory_repo = PostgresDirectoryRepository(database)
    milestone_repo = PostgresMilestoneRepository(database)
    schedule_repo = PostgresScheduleRepository(database)
    catalog = CourseCatalogService(catalog_repo)
    audit = AuditService(audit_repo, catalog)
    directory = CampusDirectoryService(directory_repo)
    milestones = StudentMilestoneService(milestone_repo, audit)
    tools = MCPTools(
        audit,
        catalog,
        directory,
        milestones,
        embedding_provider=embedding_provider,
        schedule_repository=schedule_repo,
    )
    return ToolDispatcher(tools)


def build_ingestion_repository(
    database_url: str,
) -> PostgresIngestionRepository:
    """Builds the ingestion-log repository.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        Repository for ``data_ingestion_logs``.
    """
    return PostgresIngestionRepository(Database(database_url))
