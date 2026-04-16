from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

_TAG_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_tag(tag: str) -> str:
    return _TAG_SLUG_RE.sub("-", tag.lower()).strip("-")


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)


class Bookmark(_Base):
    id: str = Field(default_factory=new_id)
    url: NonEmptyStr
    title: NonEmptyStr
    description: str | None = None
    folder_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if "://" not in v:
            raise ValueError("url must include a scheme (e.g., https://)")
        return v

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in v:
            slug = normalize_tag(raw)
            if slug and slug not in seen:
                seen.add(slug)
                out.append(slug)
        return out


class Folder(_Base):
    id: str = Field(default_factory=new_id)
    name: NonEmptyStr
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Library(_Base):
    version: str = "1.0"
    folders: list[Folder] = Field(default_factory=list)
    bookmarks: list[Bookmark] = Field(default_factory=list)
