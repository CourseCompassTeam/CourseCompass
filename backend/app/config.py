"""Application settings, loaded from environment variables.

The same codebase runs locally, in staging, and on Cloud Run. Only the
environment variables change between them.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class Settings:
    """Runtime configuration.

    Attributes:
        database_url: PostgreSQL connection string.
        clerk_secret_key: Clerk key used to verify session tokens.
        llm_provider: Name of the LLM provider (TBD).
        llm_api_key: API key for the LLM provider.
    """

    database_url: str
    clerk_secret_key: str
    llm_provider: str
    llm_api_key: str


def load_settings() -> Settings:
    """Reads settings from environment variables.

    Returns:
        The populated Settings.

    Raises:
        KeyError: If a required environment variable is missing.
    """
    raise NotImplementedError
