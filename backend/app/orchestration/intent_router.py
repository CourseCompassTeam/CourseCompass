"""Works out what a student's prompt is asking for."""


class IntentRouter:
    """Classifies a student query so the right tool can be called."""

    def route(self, query: str) -> str:
        """Determines the intent of a query.

        Out-of-scope queries (financial aid, profile changes, and so on)
        must route to a redirect, never to a guessed answer (QA-02).

        Args:
            query: The student's natural-language question.

        Returns:
            The name of the tool to call, or a redirect intent.
        """
        raise NotImplementedError
