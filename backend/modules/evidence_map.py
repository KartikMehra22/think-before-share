import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

with open(os.path.join(os.path.dirname(__file__), "../prompts/insights_analyzer.txt"), "r") as f:
    OVERALL_VERDICT_PROMPT = f.read()

def get_overall_verdict(claim_ratings: list[dict]) -> dict:
    """Use Gemini to produce an overall verdict and literacy tip."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    model = genai.GenerativeModel(model_name)
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
