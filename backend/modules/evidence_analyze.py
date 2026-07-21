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
    model = genai.GenerativeModel(model_name)
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
    logger.debug(
        "rate_claim_with_evidence: Gemini responded in %.2fs  raw_len=%d",
        time.monotonic() - t0, len(raw),
    )

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
        logger.debug("rate_claim_with_evidence: parsed status=%s", result.get("status"))
        return result
    except json.JSONDecodeError as e:
        logger.error("rate_claim_with_evidence: JSON decode error — raw=%r  err=%s", raw[:200], e)
        raise

def rate_claim_with_evidence(claim: str, evidence_snippets: list[str], sources: list[str]) -> dict:
    """Use Gemini to rate a claim against retrieved evidence."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    return gemini_retry(_do_rate_claim, claim, evidence_snippets, sources, model_name, label="rate_claim")
