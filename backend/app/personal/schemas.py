"""Pydantic schemas for Quantive Personal API."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

Relevance = Literal["high", "medium", "low"]
OppStatus = Literal[
    "potentially_relevant", "needs_information", "needs_documentation",
    "needs_verification", "reviewed", "not_applicable",
]


class FactUpsert(BaseModel):
    category: str
    key: str
    value: str = ""
    value_json: dict[str, Any] = Field(default_factory=dict)
    source: str = "onboarding"
    confidence: str = "user_reported"
    status: str = "unconfirmed"


class FactOut(FactUpsert):
    id: str
    user_id: str


class OnboardingAnswer(BaseModel):
    question_id: str
    answer: Any


class OnboardingState(BaseModel):
    status: str
    current: int
    total: int
    answers: dict[str, Any] = Field(default_factory=dict)


class OpportunityOut(BaseModel):
    id: str
    title: str
    category: str
    relevance: str
    status: str
    why: str
    needs_info: list[str] = Field(default_factory=list)
    needs_docs: list[str] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    next_action: str = ""


class TaskOut(BaseModel):
    id: str
    title: str
    reason: str = ""
    priority: str = "medium"
    status: str = "open"
    due: str = ""
    link: str = ""


class ScoreOut(BaseModel):
    score: int
    completeness: int
    open_actions: int
    opportunities: int
    doc_gaps: int
    needs_review: int
    message: str
