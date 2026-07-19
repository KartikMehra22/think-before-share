import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), "../prompts/insights_analyzer.txt"), "r") as f:
    INSIGHTS_PROMPT = f.read()

def get_insights(transcript: str) -> dict:
    """Extract media literacy insights from a transcript."""
    if not transcript:
        return {"signals": []}

    try:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
        model = genai.GenerativeModel(model_name)
        prompt = INSIGHTS_PROMPT.format(transcript=transcript)

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
    except Exception as e:
        logger.error(f"Failed to extract media literacy insights: {e}")
        return {"signals": []}

