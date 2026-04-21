from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from bookmarks_mcp.models import Library


class Storage(ABC):
    """Abstract storage backend for the Library document.

    Implementations must provide atomic `save` and serialized `transaction`
    semantics. Callers interact via `load` / `save` / `transaction` only.
    """

    @abstractmethod
    def load(self) -> Library:
        """Return the current Library. Empty Library if the backing store has no data."""

    @abstractmethod
    def save(self, library: Library) -> None:
        """Persist the Library atomically."""

    @abstractmethod
    def transaction(self) -> AbstractContextManager[Library]:
        """Context manager yielding a mutable Library; save on clean exit."""
