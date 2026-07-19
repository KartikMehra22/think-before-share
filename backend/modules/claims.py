import os
import json
import google.generativeai as genai
from models import Claim, ClaimsResponse
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

with open(os.path.join(os.path.dirname(__file__), "../prompts/claim_extractor.txt"), "r") as f:
    CLAIMS_EXTRACTION_PROMPT = f.read()

def extract_claims(transcript: str) -> list[Claim]:
    """Use Gemini to extract factual claims from a transcript."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    model = genai.GenerativeModel(model_name)
    prompt = CLAIMS_EXTRACTION_PROMPT.format(transcript=transcript)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    parsed = ClaimsResponse(**data)
    
    # M3 Hard Guardrail: Enforce max 20 claims in code
    return parsed.claims[:20]
