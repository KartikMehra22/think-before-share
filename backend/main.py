import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST before importing local modules that depend on them
load_dotenv()

import uuid
from models import AnalyzeRequest, AnalysisResult, EvidencedClaim, AnalyzeResponse, JobStatusResponse
from modules.video_resolver import extract_video_id, InvalidURLError
from modules.transcript import get_transcript
from modules.claims import extract_claims
from modules.evidence_search import search_evidence
from modules.evidence_analyze import rate_claim_with_evidence
from modules.evidence_map import get_overall_verdict
from modules.insights import get_insights

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="think-before-share API",
    description="Backend service for claim extraction and evidence verification",
    version="0.2.0",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "message": "think-before-share API is running",
        "version": "0.2.0",
    }


@app.get("/api/health")
def health_check():
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY"))
    tavily_ok = bool(os.environ.get("TAVILY_API_KEY"))
    return {
        "status": "ok",
        "gemini_configured": gemini_ok,
        "tavily_configured": tavily_ok,
    }


# In-memory job store
jobs: dict[str, JobStatusResponse] = {}

async def run_analysis_pipeline(job_id: str, url: str):
    """
    Background pipeline:
    1. Extract YouTube video ID from URL
    2. Fetch transcript
    3. Extract factual claims via Gemini
    4. Search for evidence per claim via Tavily
    5. Rate each claim via Gemini
    6. Generate overall verdict + literacy tip
    """
    try:
        # Step 1: Extract video ID
        jobs[job_id].stage = "resolving_video"
        try:
            resolved = extract_video_id(url)
            video_id = resolved["video_id"]
            logger.info(f"Extracted video ID: {video_id} for job {job_id}")
        except InvalidURLError:
            jobs[job_id].stage = "error"
            jobs[job_id].error = "invalid_url"
            return

        # Step 2: Fetch transcript
        jobs[job_id].stage = "fetching_transcript"
        jobs[job_id].stages_complete.append("resolving_video")
        transcript_data = get_transcript(video_id)
        if transcript_data["status"] == "no_transcript":
            logger.warning(f"No transcript found for video {video_id}")
            jobs[job_id].result = AnalysisResult(
                video_id=video_id,
                video_url=url,
                claims=[],
                overall_verdict="Unverifiable",
                literacy_tip="This video does not have closed captions, so we cannot extract and verify its claims."
            )
            jobs[job_id].stage = "done"
            jobs[job_id].stages_complete.extend(["fetching_transcript", "extracting_claims", "analyzing_evidence", "generating_insights"])
            return

        transcript = transcript_data["transcript"]
        logger.info(f"Fetched transcript ({len(transcript)} chars)")

        # Step 3: Extract claims via Gemini
        jobs[job_id].stage = "extracting_claims"
        jobs[job_id].stages_complete.append("fetching_transcript")
        try:
            claims = extract_claims(transcript)
            logger.info(f"Extracted {len(claims)} claims")
        except Exception as e:
            logger.error(f"Claims extraction failed: {repr(e)}")
            # M3 requires graceful degradation: return empty claims instead of crashing
            claims = []

        if not claims:
            jobs[job_id].result = AnalysisResult(
                video_id=video_id,
                video_url=url,
                claims=[],
                overall_verdict="Unverifiable",
                literacy_tip="No verifiable factual claims could be extracted from this video."
            )
            jobs[job_id].stage = "done"
            jobs[job_id].stages_complete.extend(["extracting_claims", "analyzing_evidence", "generating_insights"])
            return

        # Step 4 & 5: Search + rate each claim
        jobs[job_id].stage = "analyzing_evidence"
        jobs[job_id].stages_complete.append("extracting_claims")
        evidenced_claims: list[EvidencedClaim] = []
        claim_ratings_for_verdict = []

        for claim_obj in claims:
            claim_text = claim_obj.claim
            logger.info(f"Processing claim: {claim_text[:80]}...")

            # Search for evidence
            try:
                evidence = search_evidence(claim_text)
                snippets = evidence["snippets"]
                sources = evidence["sources"]
            except Exception as e:
                logger.warning(f"Search failed for claim '{claim_text[:50]}': {e}")
                snippets = []
                sources = []

            # Rate claim with Gemini
            if not snippets:
                # M5 Hard Guardrail: skip LLM call if no evidence is found
                status = "Insufficient Evidence"
                evidence_summary = "No search evidence was found for this claim."
            else:
                try:
                    rating = rate_claim_with_evidence(claim_text, snippets, sources)
                    status = rating.get("status", "Insufficient Evidence")
                    evidence_summary = rating.get("evidence_summary", "Unable to retrieve evidence.")
                except Exception as e:
                    logger.warning(f"Rating failed for claim '{claim_text[:50]}': {e}")
                    status = "Insufficient Evidence"
                    evidence_summary = "Evidence rating could not be completed."

            evidenced_claims.append(
                EvidencedClaim(
                    claim=claim_text,
                    speaker=claim_obj.speaker,
                    timestamp_hint=claim_obj.timestamp_hint,
                    status=status,
                    evidence_summary=evidence_summary,
                    sources=[s for s in sources if s != "tavily-synthesis"],
                )
            )
            claim_ratings_for_verdict.append({"claim": claim_text, "status": status})

        # Step 6: Overall verdict
        jobs[job_id].stage = "generating_insights"
        jobs[job_id].stages_complete.append("analyzing_evidence")
        try:
            verdict_data = get_overall_verdict(claim_ratings_for_verdict)
            overall_verdict = verdict_data.get("overall_verdict", "Unverifiable")
            literacy_tip = verdict_data.get("literacy_tip", "Always verify claims before sharing content.")
        except Exception as e:
            logger.warning(f"Verdict generation failed: {e}")
            overall_verdict = "Unverifiable"
            literacy_tip = "Always verify claims before sharing content online."

        # Step 7: Media Literacy Insights
        insights = get_insights(transcript)
        signals = insights.get("signals", [])

        jobs[job_id].result = AnalysisResult(
            video_id=video_id,
            video_url=url,
            claims=evidenced_claims,
            overall_verdict=overall_verdict,
            literacy_tip=literacy_tip,
            signals=signals,
        )
        jobs[job_id].stage = "done"
        jobs[job_id].stages_complete.append("generating_insights")
    except Exception as e:
        logger.error(f"Pipeline failed unexpectedly: {e}")
        jobs[job_id].stage = "error"
        jobs[job_id].error = str(e)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    url = request.url.strip()
    logger.info(f"Started new job {job_id} for URL: {url}")
    
    jobs[job_id] = JobStatusResponse(
        job_id=job_id,
        stage="pending",
        stages_complete=[]
    )
    
    background_tasks.add_task(run_analysis_pipeline, job_id, url)
    return AnalyzeResponse(job_id=job_id)


@app.get("/api/analyze/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]



