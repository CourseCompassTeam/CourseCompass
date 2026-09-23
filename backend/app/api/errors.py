"""Standard API error envelope.

Every error response has this shape:

    {"error": {"code": "...", "message": "...", "details": {}}}
"""

# HTTP status -> error code, per the Detailed Design.
BAD_REQUEST = (400, 'BAD_REQUEST')  # Request or tool input failed validation.
UNAUTHORIZED = (401, 'UNAUTHORIZED')  # Missing or invalid/expired session.
FORBIDDEN = (403, 'FORBIDDEN')  # Token valid, resource not owned by student.
NOT_FOUND = (404, 'NOT_FOUND')  # Student, course, or job does not exist.
# A fact could not be confirmed against the course dataset (QA-02 redirect).
UNPROCESSABLE_CONTENT = (422, 'UNPROCESSABLE_CONTENT')
TOO_MANY_REQUESTS = (429, 'TOO_MANY_REQUESTS')  # Rate limit exceeded.
INTERNAL_ERROR = (500, 'INTERNAL_ERROR')  # Unhandled server-side failure.


class ApiError(Exception):
    """An error that is returned to the client in the standard envelope.

    Attributes:
        status: HTTP status code.
        code: Error code string, e.g. 'NOT_FOUND'.
        message: Human-readable message.
        details: Optional extra information.
    """

    def __init__(self, status: int, code: str, message: str,
                 details: dict | None = None):
        raise NotImplementedError
