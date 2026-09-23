"""Student query endpoint: POST /api/v1/query."""

from fastapi import APIRouter

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
