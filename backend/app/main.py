"""CourseCompass backend entry point."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Builds the FastAPI application.

    Registers the v1 routers (query, admin ingest) and the error handlers
    that return the standard error envelope.

    Returns:
        The configured FastAPI application.
    """
    raise NotImplementedError
