"""Parsing the LinkedIn feed into a lookup keyed by contact details.

The feed is supplemental: it contributes a LinkedIn profile URL to a candidate
and nothing else. It carries no name and no candidate ID, so email and phone
are the only way in — and each row supplies only one of them in practice.
"""

from __future__ import annotations

import csv
import io
import logging

from app.domain.candidate import Candidate
from app.sources.contact_key import email_key, phone_key
from app.sources.protocols import EnrichmentOutcome

logger = logging.getLogger(__name__)

EMAIL_COLUMN = "Email"
PHONE_COLUMN = "Phone Number"
LINKEDIN_COLUMN = "Linkedin"


class LinkedInDirectory:
    """LinkedIn URLs indexed by every contact key that identifies them.

    A row is registered under its email key and its phone key, so a candidate
    resolves whichever of the two the row happened to fill in.

    Implements the Enrichment protocol: once loaded, it can attach itself to a
    set of candidates.
    """

    def __init__(self, by_email: dict[str, str], by_phone: dict[str, str]) -> None:
        self._by_email = by_email
        self._by_phone = by_phone

    def lookup(self, *, email: str | None, phone: str | None) -> str | None:
        """Email first, then phone.

        Email is the stronger identifier: globally unique, not reformatted,
        not shared between people. Phone is the fallback that resolves the rows
        whose email cell is blank.
        """
        key = email_key(email)
        if key and key in self._by_email:
            return self._by_email[key]

        key = phone_key(phone)
        if key and key in self._by_phone:
            return self._by_phone[key]

        return None

    def apply(self, candidates: list[Candidate]) -> EnrichmentOutcome:
        """Attach a profile URL to every candidate this feed knows about.

        Candidates are frozen, so this replaces rather than mutates. A
        candidate with no match keeps `linkedin_url=None`, which the renderers
        state explicitly instead of leaving blank.
        """
        enriched: list[Candidate] = []
        matched = 0

        for person in candidates:
            url = self.lookup(email=person.email, phone=person.phone)
            if url is None:
                logger.info("no LinkedIn profile matched for %s", person.name.display)
            else:
                matched += 1
            enriched.append(
                Candidate(
                    name=person.name,
                    email=person.email,
                    phone=person.phone,
                    linkedin_url=url,
                    employments=person.employments,
                )
            )

        return EnrichmentOutcome(candidates=enriched, matched=matched)

    def __len__(self) -> int:
        return len(set(self._by_email.values()) | set(self._by_phone.values()))


def parse_linkedin_feed(body: str) -> LinkedInDirectory:
    by_email: dict[str, str] = {}
    by_phone: dict[str, str] = {}

    reader = csv.DictReader(io.StringIO(body))
    for line_number, row in enumerate(reader, start=2):
        url = (row.get(LINKEDIN_COLUMN) or "").strip()
        if not url:
            logger.warning("linkedin feed line %d has no URL, skipped", line_number)
            continue

        _register(by_email, email_key(row.get(EMAIL_COLUMN)), url, line_number, "email")
        _register(by_phone, phone_key(row.get(PHONE_COLUMN)), url, line_number, "phone")

    return LinkedInDirectory(by_email, by_phone)


def _register(
    index: dict[str, str], key: str | None, url: str, line_number: int, kind: str
) -> None:
    """First row wins a contested key.

    A duplicate means two people share a contact detail, or the feed repeats
    itself. Either way, silently overwriting would attach one person's profile
    to another; keeping the first and saying so leaves the collision visible.
    """
    if not key:
        return
    if key in index and index[key] != url:
        logger.warning(
            "linkedin feed line %d reuses a %s key already claimed by %s, ignored",
            line_number,
            kind,
            index[key],
        )
        return
    index[key] = url
