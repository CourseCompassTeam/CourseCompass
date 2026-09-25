"""Student query endpoint: POST /api/v1/query."""

from fastapi import APIRouter
from fastapi import Request

from app.api.errors import ApiError
from app.api.errors import NOT_IMPLEMENTED
from app.orchestration.tool_catalog import TOOL_DEFINITIONS
from app.schemas.query import QueryRequest
from app.schemas.query import QueryResponse

router = APIRouter(prefix='/api/v1')


@router.post('/query')
def post_query(request: QueryRequest) -> QueryResponse:
    """Answers a student's natural-language question.

    Passes the query to the orchestration layer, which picks a tool,
    calls it, and assembles the response.

    Args:
        request: The student's question.

    Returns:
        A response of type 'audit', 'recommendation', or 'redirect'.

    Raises:
        ApiError: 401 if the session is invalid, 422 if a fact cannot be
            verified against the course dataset.
    """
    raise NotImplementedError


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
