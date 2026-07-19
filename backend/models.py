from pydantic import BaseModel
from typing import Literal


class Claim(BaseModel):
    claim: str
    speaker: str | None = None
    timestamp_hint: str | None = None  # e.g. "early", "midway", "near the end"


class ClaimsResponse(BaseModel):
    claims: list[Claim]


class EvidencedClaim(BaseModel):
    claim: str
    speaker: str | None = None
    timestamp_hint: str | None = None
    status: Literal["Supported", "Needs Context", "Contradicted", "Insufficient Evidence"]
    evidence_summary: str
    sources: list[str]


class AnalysisResult(BaseModel):
    video_id: str
    video_url: str
    claims: list[EvidencedClaim]
    overall_verdict: Literal["Mostly Accurate", "Mixed", "Mostly Misleading", "Unverifiable"]
    literacy_tip: str
    signals: list[str] = []


class AnalyzeRequest(BaseModel):
    url: str


class AnalyzeResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    stage: str
    stages_complete: list[str] = []
    result: AnalysisResult | None = None
    error: str | None = None
