"""Public, supervised contracts for the planning and review agents."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .schemas import Contract, EvidenceReference


class AnalysisPlan(Contract):
    selected_modalities: list[Literal["genome", "transcriptome", "proteome"]] = Field(min_length=1, max_length=3)
    questions: list[str] = Field(min_length=1, max_length=8)
    search_terms: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def nonempty_unique(self):
        if len(set(self.selected_modalities)) != len(self.selected_modalities):
            raise ValueError("selected modalities must be unique")
        if any(not value.strip() for value in (*self.questions, *self.search_terms, *self.limitations)):
            raise ValueError("plan entries must be nonempty")
        if any(len(value) > 200 for value in self.search_terms):
            raise ValueError("search terms must be short")
        return self


class ReviewIssue(Contract):
    code: str = Field(min_length=1, max_length=100)
    severity: Literal["warning", "blocking"]
    finding: str = Field(min_length=1)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list, max_length=10)


class ScientificReview(Contract):
    decision: Literal["accept", "revise", "abstain"]
    summary: str = Field(min_length=1)
    issues: list[ReviewIssue] = Field(default_factory=list, max_length=15)
    recommended_changes: list[str] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def consistent_decision(self):
        if self.decision == "accept" and any(issue.severity == "blocking" for issue in self.issues):
            raise ValueError("an accepted assessment cannot have blocking issues")
        if self.decision == "revise" and not (self.issues or self.recommended_changes):
            raise ValueError("a revision needs actionable feedback")
        if len({issue.code for issue in self.issues}) != len(self.issues):
            raise ValueError("review issue codes must be unique")
        return self
