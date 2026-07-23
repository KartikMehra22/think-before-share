import os
import json
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), "../prompts/evidence_summarizer.txt"), "r") as f:
    EVIDENCE_RATING_PROMPT = f.read()

from modules.gemini_retry import gemini_retry

def _do_rate_claim(claim: str, evidence_snippets: list[str], sources: list[str], model_name: str) -> dict:
    logger.debug("rate_claim_with_evidence: model=%s  snippets=%d", model_name, len(evidence_snippets))

    t0 = time.monotonic()
    
    if evidence_snippets:
        evidence_text = "\n\n".join(
            f"[Source {i+1}: {sources[i] if i < len(sources) else 'Unknown'}]\n{snippet}"
            for i, snippet in enumerate(evidence_snippets)
        )
        prompt = EVIDENCE_RATING_PROMPT.format(claim=claim, evidence=evidence_text)
        tools = None
    else:
        # Fallback to Gemini Native Google Search Grounding (100% Free with existing GEMINI_API_KEY)
        logger.info("rate_claim_with_evidence: activating Gemini Native Google Search Grounding for claim=%.60s", claim)
        prompt = (
            f"You are a fact-checker. Evaluate this claim using native Google Search grounding.\n"
            f"Claim: {claim}\n"
            f"Output ONLY valid JSON:\n"
            f'{{\n  "status": "Supported | Needs Context | Contradicted | Insufficient Evidence",\n'
            f'  "confidence_score": 0.85,\n'
            f'  "evidence_summary": "Concise 2-3 sentence explanation based on search findings."\n}}'
        )
        tools = [{"google_search": {}}]

    model = genai.GenerativeModel(model_name, tools=tools)

    gen_config = genai.types.GenerationConfig(
        temperature=0.1,
        max_output_tokens=512,
        response_mime_type="application/json",
    )

    response = model.generate_content(prompt, generation_config=gen_config)

    raw = response.text.strip()
    logger.debug(
        "rate_claim_with_evidence: Gemini responded in %.2fs  raw_len=%d",
        time.monotonic() - t0, len(raw),
    )

    # Robustly extract JSON block
    start_idx = raw.find('{')
    end_idx = raw.rfind('}')

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        raw_json = raw[start_idx:end_idx + 1]
    else:
        raw_json = raw

    try:
        result = json.loads(raw_json)
        logger.debug("rate_claim_with_evidence: parsed status=%s", result.get("status"))
        return result
    except json.JSONDecodeError as e:
        logger.error("rate_claim_with_evidence: JSON decode error — raw=%r  err=%s", raw[:200], e)
        raise

def rate_claim_with_evidence(claim: str, evidence_snippets: list[str], sources: list[str]) -> dict:
    """Use Gemini to rate a claim against retrieved DuckDuckGo evidence or native Google Search grounding."""
    model_name = os.environ.get("GEMINI_MODEL")
    return gemini_retry(_do_rate_claim, claim, evidence_snippets, sources, model_name, label="rate_claim")

