def get_overall_verdict(claim_ratings: list[dict]) -> dict:
    """Produce an overall verdict based purely on math/aggregation of claims."""
    if not claim_ratings:
        return {
            "overall_verdict": "Unverifiable",
            "literacy_tip": "No verifiable factual claims were found in this video."
        }

    total = len(claim_ratings)
    supported_count = sum(1 for r in claim_ratings if r["status"] == "Supported")
    contradicted_count = sum(1 for r in claim_ratings if r["status"] == "Contradicted")

    if supported_count / total > 0.5:
        verdict = "Mostly Accurate"
        tip = "Most of the claims in this video are supported by outside evidence. Still, always verify extraordinary claims yourself."
    elif contradicted_count / total > 0.5:
        verdict = "Mostly Misleading"
        tip = "Many claims in this video contradict established evidence. Be extremely skeptical of its conclusions."
    else:
        verdict = "Mixed"
        tip = "This video contains a mix of accurate and inaccurate (or unverifiable) information. Take care to verify specific points."

    return {
        "overall_verdict": verdict,
        "literacy_tip": tip
    }
