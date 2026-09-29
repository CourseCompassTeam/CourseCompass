"""Student query endpoint: POST /api/v1/query."""

from fastapi import APIRouter
from fastapi import Request

from app.api.errors import ApiError
from app.api.errors import NOT_IMPLEMENTED
from app.auth.clerk_auth import resolve_student_id
from app.orchestration.mock_query import answer_query
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from app.schemas.query import QueryRequest
from app.schemas.query import QueryResponse

router = APIRouter(prefix='/api/v1')


@router.post('/query')
def post_query(body: QueryRequest, request: Request) -> QueryResponse:
    """Answers a student's natural-language question.

    The LLM picks a tool and phrases the reply. When DATABASE_URL is
    set, tools read Cloud SQL. Otherwise hardcoded mock facts are used.

    Student identity is injected by the server from a verified Clerk
    Bearer token (QA-03). In local/staging/test, ``X-Dev-Student-Id``
    can select a seed persona when no Bearer token is sent.

    Args:
        body: The student's question.
        request: FastAPI request (reads app.state.llm_provider).

    Returns:
        A response of type 'audit', 'recommendation', or 'redirect'.

    Raises:
        ApiError: 501 if the LLM provider is not configured.
        ApiError: 401 if a Bearer token is present but invalid.
    """
    provider = getattr(request.app.state, 'llm_provider', None)
    if provider is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(
            status,
            code,
            'LLM provider is not configured. Set LLM_PROVIDER=vertex '
            'and GCP_PROJECT_ID.',
        )
    settings = getattr(request.app.state, 'settings', None)
    student_id = ''
    if settings is not None:
        student_id = resolve_student_id(request.headers, settings)

    return answer_query(
        provider,
        body.query,
        embedding_provider=getattr(
            request.app.state, 'embedding_provider', None
        ),
        tool_dispatcher=getattr(
            request.app.state, 'tool_dispatcher', None
        ),
        student_id=student_id,
    )


@router.post('/orchestration/route')
def route_query(body: QueryRequest, request: Request) -> dict:
    """Routes a query through the Vertex LLM tool chooser (smoke / staging).

    Does not call MCPTools or touch student data. Returns the model
    tool choice so the team can verify GCP Gemini wiring.

    Args:
        body: The student's question.
        request: FastAPI request (reads app.state.llm_provider).

    Returns:
        ToolChoice fields: tool, arguments, redirect.

    Raises:
        ApiError: 501 if the LLM provider is not configured.
    """
    provider = getattr(request.app.state, 'llm_provider', None)
    if provider is None:
        status, code = NOT_IMPLEMENTED
        raise ApiError(
            status,
            code,
            'LLM provider is not configured. Set LLM_PROVIDER=vertex '
            'and GCP_PROJECT_ID.',
        )
    return provider.choose_tool(body.query, TOOL_DEFINITIONS)
