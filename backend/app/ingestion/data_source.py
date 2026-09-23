"""Interface for loading data from a source into the database.

Adding a new data source (a new course catalog, a new API) means writing
a new DataSource implementation, without changing how recommendations are
generated or how other sources are handled (QA-04).
"""

import abc


class DataSource(abc.ABC):
    """A source of course, prerequisite, requirement, or transcript data."""

    @abc.abstractmethod
    def load(self, raw: bytes) -> int:
        """Parses raw input and writes it through the repository layer.

        Args:
            raw: The uploaded file contents.

        Returns:
            The number of records processed.

        Raises:
            ValueError: If the input is malformed.
        """
