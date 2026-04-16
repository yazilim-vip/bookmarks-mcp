from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Bookmark(BaseModel):
    id: str
    url: HttpUrl
    title: str
    description: str | None = None
    folder_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Folder(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Library(BaseModel):
    version: str = "1.0"
    folders: list[Folder] = Field(default_factory=list)
    bookmarks: list[Bookmark] = Field(default_factory=list)
