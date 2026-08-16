"""The JSON response schema, exactly as the specification's example defines it.

The capitalised field names and the `Linkedin_url` spelling are the
specification's, not ours. They are expressed as aliases so the Python side can
stay `snake_case`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_serializer


class NameModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # The schema has two slots, so a middle name has nowhere to go. Text output
    # keeps it; see PersonName.display.
    first_name: str | None = Field(default=None, alias="FirstName")
    last_name: str | None = Field(default=None, alias="LastName")


class JobExperienceModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: str | None = Field(default=None, alias="Role")
    start_date: str | None = Field(default=None, alias="StartDate")
    end_date: str | None = Field(default=None, alias="EndDate")
    location: str | None = Field(default=None, alias="Location")
    gap: str | None = Field(default=None, alias="Gap")

    @model_serializer(mode="wrap")
    def _omit_absent_gap(self, handler: Any) -> dict[str, Any]:
        """Drop `Gap` when there is none, rather than emitting it as null.

        The example output omits the key on a job with no preceding gap, and
        `"Gap": null` on ten of twelve jobs is noise. Every other field stays
        present so the schema is stable to consume.
        """
        data = handler(self)
        for key in ("Gap", "gap"):
            if data.get(key) is None:
                data.pop(key, None)
        return data


class CandidateModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: NameModel = Field(alias="Name")
    linkedin_url: str | None = Field(default=None, alias="Linkedin_url")
    job_experience: list[JobExperienceModel] = Field(
        default_factory=list, alias="JobExperience"
    )
