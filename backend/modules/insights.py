import os
import json
import time
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), "../prompts/insights_analyzer.txt"), "r") as f:
    INSIGHTS_PROMPT = f.read()

from modules.gemini_retry import gemini_retry

def _do_get_insights(transcript: str, model_name: str) -> dict:
    try:
        t0 = time.monotonic()
        model = genai.GenerativeModel(model_name)
        prompt = INSIGHTS_PROMPT.replace("{transcript}", transcript)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )

        gemini_elapsed = time.monotonic() - t0
        raw = response.text.strip()
        logger.info(
            "get_insights: Gemini responded in %.2fs  raw_len=%d chars",
            gemini_elapsed, len(raw),
        )

        # Robustly extract JSON block
        start_idx = raw.find('{')
        end_idx = raw.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_json = raw[start_idx:end_idx + 1]
        else:
            raw_json = raw
            logger.warning("get_insights: could not find JSON braces — attempting parse of full text")

        result = json.loads(raw_json)
        signals = result.get("signals", [])
        logger.info("get_insights: %d signal(s) extracted", len(signals))
        return result

    except Exception as e:
        # Don't catch ResourceExhausted here so it bubbles up to the retry wrapper
        from google.api_core.exceptions import ResourceExhausted
        if isinstance(e, ResourceExhausted):
            raise
        logger.error("get_insights: failed — %s", repr(e))
        return {"signals": []}


def get_insights(transcript: str) -> dict:
    """Extract media literacy insights from a transcript."""
    if not transcript:
        logger.info("get_insights: transcript is empty — returning empty signals")
        return {"signals": []}

    model_name = os.environ.get("GEMINI_MODEL")
    logger.info("get_insights: model=%s  transcript_len=%d chars", model_name, len(transcript))
    
    return gemini_retry(_do_get_insights, transcript, model_name, label="get_insights")
