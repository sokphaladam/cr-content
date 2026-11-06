"""The research brief (spec 5.2). A claim's status is never taken from a model's word: claims.settle() derives it
from the evidence attached, and evidence can only point at a stored source with an excerpt."""
from typing import Literal

from pydantic import BaseModel, Field

VERSION = 1
CLAIM_TYPES = ("date", "person", "location", "event", "cause", "consequence", "quantity", "interpretation")
STATUSES = ("supported", "disputed", "uncertain", "unsupported")
ROLES = ("primary", "scholarly_secondary", "museum_or_archive", "reference")


class ResearchSource(BaseModel):
    id: str
    title: str = ""
    publisher: str = ""
    author: str = ""
    url: str = ""
    source_type: str = ""            # "web", "encyclopedia", "user"
    provider: str = ""               # "google_search" (Gemini grounding), "wikipedia", "user"
    publication_date: str = ""
    accessed_at: str = ""
    excerpts: list[str] = []         # what the source says (Wikipedia: its intro; grounding: the text Google tied to it)
    note: str = ""                   # the creator's note
    source_role: Literal["primary", "scholarly_secondary", "museum_or_archive", "reference"] = "reference"
    license_note: str = ""
    retrieval_error: str = ""        # the page couldn't be read; it can't be evidence until an excerpt is added


class Evidence(BaseModel):
    source_id: str
    excerpt: str = ""
    stance: Literal["supports", "disputes"] = "supports"


class HistoricalClaim(BaseModel):
    id: str
    claim_text: str
    claim_type: str = "event"
    status: Literal["supported", "disputed", "uncertain", "unsupported"] = "unsupported"
    importance: Literal["central", "supporting", "optional"] = "supporting"
    evidence: list[Evidence] = []
    source_ids: list[str] = []       # derived from evidence (settle)
    notes: str = ""
    script_scene_ids: list[str] = []
    locked: bool = False             # edited by the creator: a re-check keeps its evidence and status


class TimelineEvent(BaseModel):
    date: str = ""
    event: str = ""


class Contradiction(BaseModel):
    claim_id: str = ""
    note: str = ""
    source_ids: list[str] = []


class ResearchBrief(BaseModel):
    version: int = VERSION
    id: str
    topic: str = ""
    project_kind: str = ""           # "draft", "long" or "topic"
    project_ref: str = ""
    created_at: str = ""
    updated_at: str = ""
    period: str = ""
    places: list[str] = []
    people: list[str] = []
    entities: list[str] = []
    summary: str = ""
    timeline_events: list[TimelineEvent] = []
    claims: list[HistoricalClaim] = []
    sources: list[ResearchSource] = []
    contradictions: list[Contradiction] = []
    open_questions: list[str] = []
    research_status: Literal["draft", "needs_review", "approved"] = "draft"
    revision: int = 0                # +1 on every save
    approved_revision: int = 0       # the revision the creator approved (0 = never)
    approved_at: str = ""
    provider_notes: list[str] = Field(default_factory=list)  # which providers failed or were skipped, in plain words
    written_script: list[dict] = []  # a topic brief: the script written from it (history/script.py), scene by scene
