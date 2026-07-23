import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
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


def _step(job_id: str, stage: str, label: str) -> float:
    """Update job stage, log a header, and return a start timestamp."""
    jobs[job_id].stage = stage
    logger.info("┌─ [%s] STEP: %s", job_id[:8], label)
    return time.monotonic()


def _done(job_id: str, t0: float, label: str):
    """Log the elapsed time for a completed step."""
    elapsed = time.monotonic() - t0
    logger.info("└─ [%s] DONE: %s  (%.2fs)", job_id[:8], label, elapsed)


def _process_single_claim(idx: int, total: int, claim_obj, prefix: str) -> tuple[EvidencedClaim, dict]:
    claim_text = claim_obj.claim
    search_q = claim_obj.search_query
    claim_start = time.monotonic()
    logger.info("   %s ── [PARALLEL] claim[%d/%d]: %.80s", prefix, idx, total, claim_text)

    try:
        evidence = search_evidence(claim_text, search_query=search_q)
        snippets = evidence["snippets"]
        sources = evidence["sources"]
        logger.info(
            "      %s search: %d snippet(s) from %d source(s)",
            prefix, len(snippets), len([s for s in sources if s != "tavily-synthesis"])
        )
    except Exception as e:
        logger.warning("      %s search FAILED: %s", prefix, e)
        snippets = []
        sources = []

    try:
        rating = rate_claim_with_evidence(claim_text, snippets, sources)
        status = rating.get("status", "Insufficient Evidence")
        confidence = float(rating.get("confidence_score", 0.75))
        evidence_summary = rating.get("evidence_summary", "Evaluation complete.")
        logger.info("      %s rating: status=%s  confidence=%.2f", prefix, status, confidence)
    except Exception as e:
        logger.warning("      %s rating FAILED: %s", prefix, e)
        status = "Needs Context" if snippets else "Insufficient Evidence"
        confidence = 0.65 if snippets else 0.40
        evidence_summary = "Evidence rating could not be completed automatically."

    elapsed_claim = time.monotonic() - claim_start
    logger.info("      %s claim[%d] DONE in %.2fs  verdict=%s", prefix, idx, elapsed_claim, status)

    ev_claim = EvidencedClaim(
        claim=claim_text,
        search_query=search_q,
        speaker=claim_obj.speaker,
        timestamp_hint=claim_obj.timestamp_hint,
        status=status,
        confidence_score=confidence,
        evidence_summary=evidence_summary,
        sources=[s for s in sources if s != "tavily-synthesis"],
    )
    rating_dict = {
        "claim": claim_text,
        "status": status,
        "confidence_score": confidence,
    }
    return ev_claim, rating_dict


def run_analysis_pipeline(job_id: str, url: str):
    """
    Background pipeline:
    1. Extract YouTube video ID from URL
    2. Fetch transcript
    3. Extract factual claims via Gemini
    4. Search for evidence per claim via Tavily (Parallelized)
    5. Rate each claim via Gemini (Parallelized)
    6. Generate overall verdict + literacy tip
    7. Extract media literacy signals + deepfake risk
    """
    pipeline_start = time.monotonic()
    prefix = f"[{job_id[:8]}]"
    logger.info("════════════════════════════════════════")
    logger.info("%s PIPELINE START  url=%s", prefix, url)
    logger.info("════════════════════════════════════════")

    try:
        # ── Step 1: Resolve video ID ─────────────────────────────────────────
        t0 = _step(job_id, "resolving_video", "Resolve video ID")
        try:
            resolved = extract_video_id(url)
            video_id = resolved["video_id"]
            logger.info("   %s video_id=%s", prefix, video_id)
            _done(job_id, t0, "Resolve video ID")
        except InvalidURLError as e:
            logger.error("   %s Invalid URL: %s", prefix, e)
            jobs[job_id].stage = "error"
            jobs[job_id].error = "invalid_url"
            return

        # ── Step 2: Fetch transcript ─────────────────────────────────────────
        t0 = _step(job_id, "fetching_transcript", "Fetch transcript")
        jobs[job_id].stages_complete.append("resolving_video")
        transcript_data = get_transcript(video_id)

        if transcript_data["status"] == "no_transcript":
            logger.warning("   %s No transcript available for video_id=%s", prefix, video_id)
            jobs[job_id].result = AnalysisResult(
                video_id=video_id,
                video_url=url,
                claims=[],
                overall_verdict="Unverifiable",
                literacy_tip="This video does not have closed captions, so we cannot extract and verify its claims."
            )
            jobs[job_id].stage = "done"
            jobs[job_id].stages_complete.extend([
                "fetching_transcript", "extracting_claims",
                "analyzing_evidence", "generating_insights"
            ])
            logger.info("   %s Pipeline ended early: no transcript.", prefix)
            return

        transcript = transcript_data["transcript"]
        _done(job_id, t0, f"Fetch transcript ({len(transcript)} chars)")

        # ── Step 3: Extract claims ────────────────────────────────────────────
        t0 = _step(job_id, "extracting_claims", "Extract claims (Gemini)")
        jobs[job_id].stages_complete.append("fetching_transcript")
        try:
            claims = extract_claims(transcript)
            _done(job_id, t0, f"Extract claims → {len(claims)} claims found")
            for i, c in enumerate(claims):
                logger.info("   %s  claim[%d]: %.90s", prefix, i + 1, c.claim)
        except Exception as e:
            logger.error("   %s Claims extraction failed: %s", prefix, repr(e))
            claims = []
            _done(job_id, t0, "Extract claims → FAILED (graceful degradation)")

        if not claims:
            logger.warning("   %s No claims extracted. Returning Unverifiable.", prefix)
            jobs[job_id].result = AnalysisResult(
                video_id=video_id,
                video_url=url,
                claims=[],
                overall_verdict="Unverifiable",
                literacy_tip="No verifiable factual claims could be extracted from this video."
            )
            jobs[job_id].stage = "done"
            jobs[job_id].stages_complete.extend([
                "extracting_claims", "analyzing_evidence", "generating_insights"
            ])
            return

        # ── Step 4 & 5: Parallel Search + Rate each claim ─────────────────────
        t0 = _step(job_id, "analyzing_evidence", f"Analyze evidence for {len(claims)} claims (Parallel)")
        jobs[job_id].stages_complete.append("extracting_claims")
        evidenced_claims: list[EvidencedClaim] = []
        claim_ratings_for_verdict = []

        # Execute parallel claim verification tasks
        with ThreadPoolExecutor(max_workers=min(len(claims), 5)) as executor:
            futures = [
                executor.submit(_process_single_claim, idx, len(claims), claim_obj, prefix)
                for idx, claim_obj in enumerate(claims, start=1)
            ]
            results = [f.result() for f in futures]

        for ev_claim, rating_dict in results:
            evidenced_claims.append(ev_claim)
            claim_ratings_for_verdict.append(rating_dict)

        _done(job_id, t0, "Analyze evidence (Parallel execution finished)")

        # ── Step 6 & 7: Media literacy signals, Deepfake Risk & Verdict ────────
        t0 = _step(job_id, "generating_insights", "Extract signals + deepfake risk + calculate verdict")
        jobs[job_id].stages_complete.append("analyzing_evidence")
        
        signals = []
        detailed_signals = []
        deepfake_risk = "Low Risk"
        deepfake_indicators = []
        shareability_recommendation = "Verify key factual claims before forwarding or posting."

        try:
            insights = get_insights(transcript)
            signals = insights.get("signals", [])
            detailed_signals = insights.get("detailed_signals", [])
            deepfake_risk = insights.get("deepfake_risk", "Low Risk")
            deepfake_indicators = insights.get("deepfake_indicators", [])
            shareability_recommendation = insights.get(
                "shareability_recommendation",
                "Verify key factual claims before forwarding or posting."
            )
            logger.info("   %s signals: %d found  deepfake_risk=%s", prefix, len(signals), deepfake_risk)
        except Exception as e:
            logger.warning("   %s Insights FAILED: %s", prefix, e)

        try:
            verdict_data = get_overall_verdict(claim_ratings_for_verdict, signals_count=len(signals))
            overall_verdict = verdict_data.get("overall_verdict", "Unverifiable")
            trust_score = verdict_data.get("trust_score", 50)
            credibility_tier = verdict_data.get("credibility_tier", "Caution / Mixed")
            literacy_tip = verdict_data.get("literacy_tip", "Always verify claims before sharing content.")
            logger.info("   %s trust_score=%d  tier=%s  verdict=%s", prefix, trust_score, credibility_tier, overall_verdict)
            _done(job_id, t0, f"Generate verdict → {overall_verdict} ({trust_score}%)")
        except Exception as e:
            logger.warning("   %s Verdict generation FAILED: %s", prefix, e)
            overall_verdict = "Unverifiable"
            trust_score = 50
            credibility_tier = "Unverifiable"
            literacy_tip = "Always verify claims before sharing content online."
            _done(job_id, t0, "Generate verdict → FAILED (fallback)")

        jobs[job_id].result = AnalysisResult(
            video_id=video_id,
            video_url=url,
            claims=evidenced_claims,
            trust_score=trust_score,
            credibility_tier=credibility_tier,
            overall_verdict=overall_verdict,
            literacy_tip=literacy_tip,
            shareability_recommendation=shareability_recommendation,
            deepfake_risk=deepfake_risk,
            deepfake_indicators=deepfake_indicators,
            signals=signals,
            detailed_signals=detailed_signals,
        )
        jobs[job_id].stage = "done"
        jobs[job_id].stages_complete.append("generating_insights")

        total = time.monotonic() - pipeline_start
        verdict_counts = {}
        for cr in claim_ratings_for_verdict:
            verdict_counts[cr["status"]] = verdict_counts.get(cr["status"], 0) + 1

        logger.info("════════════════════════════════════════")
        logger.info("%s PIPELINE COMPLETE in %.2fs", prefix, total)
        logger.info("%s   Claims: %d  |  Verdict: %s", prefix, len(evidenced_claims), overall_verdict)
        logger.info("%s   Breakdown: %s", prefix, verdict_counts)
        logger.info("════════════════════════════════════════")

    except Exception as e:
        total = time.monotonic() - pipeline_start
        logger.error("════════════════════════════════════════")
        logger.error("%s PIPELINE CRASHED after %.2fs: %s", prefix, total, repr(e), exc_info=True)
        logger.error("════════════════════════════════════════")
        jobs[job_id].stage = "error"
        jobs[job_id].error = str(e)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    url = request.url.strip()
    logger.info("NEW JOB  job_id=%s  url=%s", job_id, url)

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
