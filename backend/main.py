import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables FIRST before importing local modules that depend on them
load_dotenv()

from models import AnalyzeRequest, AnalysisResult, EvidencedClaim
from modules.video_resolver import extract_video_id, InvalidURLError
from modules.transcript import get_transcript
from modules.claims import extract_claims
from modules.evidence_search import search_evidence
from modules.evidence_analyze import rate_claim_with_evidence
from modules.evidence_map import get_overall_verdict

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


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_video(request: AnalyzeRequest):
    """
    Full pipeline:
    1. Extract YouTube video ID from URL
    2. Fetch transcript
    3. Extract factual claims via Gemini
    4. Search for evidence per claim via Tavily
    5. Rate each claim via Gemini
    6. Generate overall verdict + literacy tip
    """
    url = request.url.strip()
    logger.info(f"Received analyze request for URL: {url}")

    # Step 1: Extract video ID
    try:
        resolved = extract_video_id(url)
        video_id = resolved["video_id"]
        logger.info(f"Extracted video ID: {video_id}")
    except InvalidURLError:
        raise HTTPException(status_code=400, detail="invalid_url")

    # Step 2: Fetch transcript
    try:
        transcript = get_transcript(video_id)
        logger.info(f"Fetched transcript ({len(transcript)} chars)")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Step 3: Extract claims via Gemini
    try:
        claims = extract_claims(transcript)
        logger.info(f"Extracted {len(claims)} claims")
    except Exception as e:
        logger.error(f"Claims extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Claim extraction failed: {str(e)}")

    if not claims:
        raise HTTPException(
            status_code=422,
            detail="No verifiable factual claims could be extracted from this video."
        )

    # Step 4 & 5: Search + rate each claim
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
    try:
        verdict_data = get_overall_verdict(claim_ratings_for_verdict)
        overall_verdict = verdict_data.get("overall_verdict", "Unverifiable")
        literacy_tip = verdict_data.get("literacy_tip", "Always verify claims before sharing content.")
    except Exception as e:
        logger.warning(f"Verdict generation failed: {e}")
        overall_verdict = "Unverifiable"
        literacy_tip = "Always verify claims before sharing content online."

    return AnalysisResult(
        video_id=video_id,
        video_url=url,
        claims=evidenced_claims,
        overall_verdict=overall_verdict,
        literacy_tip=literacy_tip,
    )
