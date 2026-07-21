import os
import json
import time
import logging
import google.generativeai as genai
from models import Claim, ClaimsResponse
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), "../prompts/claim_extractor.txt"), "r") as f:
    CLAIMS_EXTRACTION_PROMPT = f.read()

from modules.gemini_retry import gemini_retry

def _do_extract_claims(transcript: str, model_name: str) -> list[Claim]:
    logger.info("extract_claims: model=%s  transcript_len=%d chars", model_name, len(transcript))

    t0 = time.monotonic()
    model = genai.GenerativeModel(model_name)
    prompt = CLAIMS_EXTRACTION_PROMPT.replace("{transcript}", transcript)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    gemini_elapsed = time.monotonic() - t0
    raw = response.text.strip()
    logger.info(
        "extract_claims: Gemini responded in %.2fs  raw_len=%d chars",
        gemini_elapsed, len(raw),
    )

    # Robustly extract JSON block
    start_idx = raw.find('{')
    end_idx = raw.rfind('}')

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        raw_json = raw[start_idx:end_idx + 1]
    else:
        raw_json = raw
        logger.warning("extract_claims: could not find JSON braces in response — attempting parse of full text")

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        logger.error(
            "extract_claims: JSON decode failed — err=%s  raw_preview=%r",
            e, raw[:300],
        )
        raise ValueError(f"Failed to parse JSON: {e}")

    parsed = ClaimsResponse(**data)

    # M3 Hard Guardrail: Enforce max 20 claims in code
    claims = parsed.claims[:20]
    logger.info("extract_claims: %d claim(s) parsed (capped at 20)", len(claims))
    return claims


def extract_claims(transcript: str) -> list[Claim]:
    """Use Gemini to extract factual claims from a transcript."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    return gemini_retry(_do_extract_claims, transcript, model_name, label="extract_claims")
