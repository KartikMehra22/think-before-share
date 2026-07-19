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
        prompt = INSIGHTS_PROMPT.replace("{transcript}", transcript)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )

        raw = response.text.strip()
        
        # Robustly extract JSON block
        start_idx = raw.find('{')
        end_idx = raw.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_json = raw[start_idx:end_idx+1]
        else:
            raw_json = raw

        return json.loads(raw_json)
    except Exception as e:
        logger.error(f"Failed to extract media literacy insights: {e}")
        return {"signals": []}

