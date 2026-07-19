import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

with open(os.path.join(os.path.dirname(__file__), "../prompts/evidence_summarizer.txt"), "r") as f:
    EVIDENCE_RATING_PROMPT = f.read()

def rate_claim_with_evidence(claim: str, evidence_snippets: list[str], sources: list[str]) -> dict:
    """Use Gemini to rate a claim against retrieved evidence."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
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
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
