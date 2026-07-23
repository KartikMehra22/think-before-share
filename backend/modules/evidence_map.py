# Named weights for claim evaluation scoring
WEIGHT_SUPPORTED = 100.0
WEIGHT_NEEDS_CONTEXT = 55.0
WEIGHT_INSUFFICIENT = 40.0
WEIGHT_CONTRADICTED = 0.0

def get_overall_verdict(claim_ratings: list[dict], signals_count: int = 0) -> dict:
    """
    Produce a mathematical trust_score (0-100), overall verdict, and credibility tier
    based on claim ratings and media literacy signals.
    """
    if not claim_ratings:
        return {
            "trust_score": 0,
            "credibility_tier": "Unverifiable",
            "overall_verdict": "Unverifiable",
            "literacy_tip": "No verifiable factual claims were found in this video."
        }

    total = len(claim_ratings)
    # Weight score calculation per claim
    total_score = 0.0
    for r in claim_ratings:
        status = r.get("status", "Insufficient Evidence")
        confidence = float(r.get("confidence_score", 0.7))

        if status == "Supported":
            item_score = WEIGHT_SUPPORTED * confidence
        elif status == "Needs Context":
            item_score = WEIGHT_NEEDS_CONTEXT * confidence
        elif status == "Insufficient Evidence":
            item_score = WEIGHT_INSUFFICIENT
        else:  # Contradicted
            item_score = WEIGHT_CONTRADICTED

        total_score += item_score

    raw_trust_score = total_score / total

    # Subtle penalty for media literacy red flags (max 15% penalty)
    flag_penalty = min(signals_count * 3, 15)
    trust_score = max(0, min(100, int(round(raw_trust_score - flag_penalty))))

    if trust_score >= 80:
        verdict = "Mostly Accurate"
        tier = "Verified / High Credibility"
        tip = "Most claims in this video are supported by outside evidence. Keep checking sources for new developments."
    elif trust_score >= 50:
        verdict = "Mixed"
        tier = "Caution / Mixed"
        tip = "This content presents a mixture of verified facts and unconfirmed or missing context. Double-check specific statements."
    else:
        verdict = "Mostly Misleading"
        tier = "Misleading / Low Credibility"
        tip = "A significant portion of the claims in this video contradict evidence or lack context. Exercise high skepticism before sharing."

    return {
        "trust_score": trust_score,
        "credibility_tier": tier,
        "overall_verdict": verdict,
        "literacy_tip": tip,
    }

