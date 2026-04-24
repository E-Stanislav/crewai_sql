from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    kind: Literal["syntax", "schema", "performance", "style", "other"] = "other"
    severity: Literal["low", "medium", "high"] = "medium"
    message: str
    recommendation: str | None = None


class ReviewMetadata(BaseModel):
    database: str = "unknown"
    explain_duration_ms: float | None = None
    estimated_cost: float | None = None
    query_hash: str


class FileReviewResult(BaseModel):
    file_path: str
    status: Literal["OK", "WARNING", "ERROR"] = "WARNING"
    summary: str
    issues: list[ReviewIssue] = Field(default_factory=list)
    improved_sql: str | None = None
    metadata: ReviewMetadata


class SummaryStats(BaseModel):
    total_files: int = 0
    ok: int = 0
    warning: int = 0
    error: int = 0
    top_heavy_queries: list[tuple[str, float]] = Field(default_factory=list)
    issues_by_kind: dict[str, int] = Field(default_factory=dict)
