from pydantic import BaseModel
from typing import Literal


class Claim(BaseModel):
    claim: str
    search_query: str | None = None
    speaker: str | None = None
    timestamp_hint: str | None = None  # e.g. "early", "midway", "near the end"


class ClaimsResponse(BaseModel):
    claims: list[Claim]


class EvidencedClaim(BaseModel):
    claim: str
    search_query: str | None = None
    speaker: str | None = None
    timestamp_hint: str | None = None
    status: Literal["Supported", "Needs Context", "Contradicted", "Insufficient Evidence"]
    confidence_score: float = 0.5
    evidence_summary: str
    sources: list[str]


class MediaSignal(BaseModel):
    signal_key: str
    label: str
    quote_snippet: str | None = None
    explanation: str | None = None


class AnalysisResult(BaseModel):
    video_id: str
    video_url: str
    claims: list[EvidencedClaim]
    trust_score: int = 50
    credibility_tier: str = "Caution / Mixed"
    overall_verdict: Literal["Mostly Accurate", "Mixed", "Mostly Misleading", "Unverifiable"]
    literacy_tip: str
    shareability_recommendation: str = "Verify key claims before forwarding or posting."
    deepfake_risk: Literal["Low Risk", "Medium Risk", "High Risk"] = "Low Risk"
    deepfake_indicators: list[str] = []
    signals: list[str] = []
    detailed_signals: list[MediaSignal] = []


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

