import os
import json
import google.generativeai as genai
from models import Claim, ClaimsResponse

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

CLAIMS_EXTRACTION_PROMPT = """You are a media literacy expert analyzing YouTube video transcripts.

Your task: Extract the 3-6 most important FACTUAL CLAIMS from the transcript below.

Rules:
- Focus on VERIFIABLE factual statements (statistics, named entities, events, scientific claims, historical facts).
- Ignore opinions, predictions, rhetorical questions, and introductions.
- Each claim should be a standalone sentence that can be searched for independently.
- If you can identify a speaker context or approximate timing, include it.
- Output ONLY valid JSON — no markdown, no explanation.

Output format:
{{
  "claims": [
    {{
      "claim": "The factual claim as a clear, standalone sentence.",
      "speaker": "Speaker name if identifiable, or null",
      "timestamp_hint": "early | midway | near the end | null"
    }}
  ]
}}

Transcript:
{transcript}
"""

EVIDENCE_RATING_PROMPT = """You are a fact-checker evaluating a claim against web search evidence.

Claim: {claim}

Search Evidence (snippets from web sources):
{evidence}

Based on the evidence above, rate the claim as one of:
- "Supported": The evidence clearly backs the claim.
- "Needs Context": The claim is partially true or misleading without additional context.
- "Contradicted": The evidence clearly contradicts the claim.
- "Insufficient Evidence": The search results don't provide enough information to evaluate the claim.

Provide a concise 2-3 sentence evidence summary explaining your rating.

Output ONLY valid JSON — no markdown, no explanation:
{{
  "status": "Supported | Needs Context | Contradicted | Insufficient Evidence",
  "evidence_summary": "Your 2-3 sentence explanation here."
}}
"""

OVERALL_VERDICT_PROMPT = """You are a media literacy assistant.

Given these claim ratings for a video:
{claim_ratings}

1. Determine an overall verdict for the video:
   - "Mostly Accurate": Most claims are supported.
   - "Mixed": A mix of supported, needs context, and/or contradicted claims.
   - "Mostly Misleading": Most claims are contradicted or need significant context.
   - "Unverifiable": Most claims lack sufficient evidence to evaluate.

2. Write ONE short, actionable media literacy tip (1-2 sentences) for viewers of this video.

Output ONLY valid JSON — no markdown:
{{
  "overall_verdict": "...",
  "literacy_tip": "..."
}}
"""


def extract_claims(transcript: str) -> list[Claim]:
    """Use Gemini to extract factual claims from a transcript."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = CLAIMS_EXTRACTION_PROMPT.format(transcript=transcript)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    raw = response.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    parsed = ClaimsResponse(**data)
    return parsed.claims


def rate_claim_with_evidence(claim: str, evidence_snippets: list[str], sources: list[str]) -> dict:
    """Use Gemini to rate a claim against retrieved evidence."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    evidence_text = "\n\n".join(
        f"[Source {i+1}: {sources[i] if i < len(sources) else 'Unknown'}]\n{snippet}"
        for i, snippet in enumerate(evidence_snippets)
    )

    prompt = EVIDENCE_RATING_PROMPT.format(claim=claim, evidence=evidence_text)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=512,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def get_overall_verdict(claim_ratings: list[dict]) -> dict:
    """Use Gemini to produce an overall verdict and literacy tip."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    ratings_text = "\n".join(
        f"- Claim: \"{r['claim']}\" → {r['status']}"
        for r in claim_ratings
    )

    prompt = OVERALL_VERDICT_PROMPT.format(claim_ratings=ratings_text)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=512,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
