"""The domain vocabulary, as defined in CONTEXT.md.

Nothing in this package knows about HTTP, CSV, SQL or the shape of the
upstream feeds. It is the layer both the CLI and the API render from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# The wire format the feeds use and the exercise's example output specifies.
DATE_FORMAT = "%b/%d/%Y"


@dataclass(frozen=True)
class PersonName:
    given_name: str | None
    family_name: str | None
    formatted_name: str | None

    @property
    def display(self) -> str:
        """The full name, middle initial included.

        The JSON schema is fixed at FirstName/LastName by the specification, so
        a middle name has nowhere to go there. Text output is ours to shape, so
        it keeps what the feed gave us.
        """
        if self.formatted_name:
            return self.formatted_name
        parts = [p for p in (self.given_name, self.family_name) if p]
        return " ".join(parts)


@dataclass(frozen=True)
class Employment:
    role: str | None
    start_date: date | None
    end_date: date | None
    location: str | None
    is_current: bool = False

    @property
    def is_datable(self) -> bool:
        """Whether this employment can take part in gap arithmetic.

        An ongoing role has no end date by definition, and nothing follows it
        in the timeline, so its missing end is not a hole. A missing start
        always is.
        """
        return self.start_date is not None and (self.end_date is not None or self.is_current)


@dataclass(frozen=True)
class Candidate:
    name: PersonName
    email: str | None
    phone: str | None
    linkedin_url: str | None
    employments: tuple[Employment, ...]
