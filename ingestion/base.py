"""
Every source type (PDF, GitHub repo, YouTube video, website, paper) gets
normalized into this common shape before it reaches the chunker/vector
store/graph store. That's what lets vector search, graph search, and the
context merger treat all sources uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NormalizedDocument:
    source_id: str                      # stable id, e.g. hash of URL/path
    source_type: str                    # "pdf" | "github" | "youtube" | "web" | "paper"
    title: str
    text: str                           # full extracted text
    url: str | None = None
    authors: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # For sources with natural sub-structure (video timestamps, code files,
    # paper sections) — used later for citation grounding.
    sections: list[dict[str, Any]] = field(default_factory=list)


class BaseIngestor(ABC):
    """Subclass this for each source type."""

    source_type: str = "base"

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Return True if this ingestor knows how to process `source`
        (a URL, file path, or repo identifier)."""
        raise NotImplementedError

    @abstractmethod
    def ingest(self, source: str) -> NormalizedDocument:
        """Fetch + parse the source and return a NormalizedDocument.
        TODO: raise a clear IngestionError on failure rather than
        letting arbitrary exceptions bubble up."""
        raise NotImplementedError


class IngestionError(Exception):
    pass
