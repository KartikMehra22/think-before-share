import os
import sys
import json
import time

# Force USE_CACHE=false in environment variables to ensure live API latency measurements
os.environ["USE_CACHE"] = "false"

# Add backend directory to sys.path to enable imports
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from llm import extract_claims, rate_claim_with_evidence, get_overall_verdict
    from search import search_evidence
except ModuleNotFoundError as e:
    print(f"Error importing modules: {e}")
    print("\nIt looks like python is not running inside the project virtual environment.")
    print("Please resolve this by either:")
    print("  1. Activating the virtual environment:")
    print("     source backend/.venv/bin/activate")
    print("     python backend/fixtures/time_pipeline.py")
    print("  2. Running the script directly with the virtual environment interpreter:")
    print("     backend/.venv/bin/python backend/fixtures/time_pipeline.py\n")
    sys.exit(1)


def main():
    fixture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_transcript.json")
    if not os.path.exists(fixture_path):
        print(f"Error: Demo transcript fixture not found at {fixture_path}.")
        print("Please run save_demo_fixture.py first.")
        sys.exit(1)

    print(f"Loading transcript fixture from: {fixture_path}")
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    transcript = fixture_data.get("transcript", "")
    if not transcript:
        print("Error: Transcript inside demo_transcript.json is empty.")
        sys.exit(1)

    print(f"Transcript length: {len(transcript)} characters.")
    print("Running pipeline profiling (USE_CACHE=false is enforced)...")

    # Ensure API keys are present
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
    if not os.environ.get("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY environment variable is not set.")
        sys.exit(1)

    total_start = time.perf_counter()

    # --- Stage 1: Claim Extraction ---
    print("\n[1/4] Extracting claims...")
    stage1_start = time.perf_counter()
    try:
        claims = extract_claims(transcript)
        stage1_time = time.perf_counter() - stage1_start
        print(f"-> Extracted {len(claims)} factual claims in {stage1_time:.2f}s.")
    except Exception as e:
        print(f"Error during claim extraction: {e}")
        sys.exit(1)

    if not claims:
        print("Error: No claims extracted from transcript. Cannot proceed.")
        sys.exit(1)

    # --- Stage 2: Evidence Search ---
    print("\n[2/4] Searching evidence for claims...")
    stage2_start = time.perf_counter()
    claims_evidence = []
    for i, claim_obj in enumerate(claims):
        claim_text = claim_obj.claim
        print(f"  ({i+1}/{len(claims)}) Searching for: '{claim_text[:60]}...'")
        try:
            evidence = search_evidence(claim_text)
            claims_evidence.append((claim_obj, evidence))
        except Exception as e:
            print(f"  Warning: Search failed for claim {i+1}: {e}")
            claims_evidence.append((claim_obj, {"snippets": [], "sources": []}))
    stage2_time = time.perf_counter() - stage2_start
    print(f"-> Searched evidence in {stage2_time:.2f}s.")

    # --- Stage 3: Evidence Rating ---
    print("\n[3/4] Rating claims with evidence...")
    stage3_start = time.perf_counter()
    claim_ratings_for_verdict = []
    for i, (claim_obj, evidence) in enumerate(claims_evidence):
        claim_text = claim_obj.claim
        print(f"  ({i+1}/{len(claims)}) Rating: '{claim_text[:60]}...'")
        try:
            rating = rate_claim_with_evidence(claim_text, evidence["snippets"], evidence["sources"])
            status = rating.get("status", "Insufficient Evidence")
        except Exception as e:
            print(f"  Warning: Rating failed for claim {i+1}: {e}")
            status = "Insufficient Evidence"
        claim_ratings_for_verdict.append({"claim": claim_text, "status": status})
    stage3_time = time.perf_counter() - stage3_start
    print(f"-> Rated claims in {stage3_time:.2f}s.")

    # --- Stage 4: Overall Verdict ---
    print("\n[4/4] Generating overall verdict...")
    stage4_start = time.perf_counter()
    try:
        verdict_data = get_overall_verdict(claim_ratings_for_verdict)
        stage4_time = time.perf_counter() - stage4_start
        print(f"-> Overall verdict: {verdict_data.get('overall_verdict')} in {stage4_time:.2f}s.")
    except Exception as e:
        print(f"Error generating overall verdict: {e}")
        sys.exit(1)

    total_time = time.perf_counter() - total_start

    # Print formatting helpers
    sep = "+" + "-" * 32 + "+" + "-" * 17 + "+" + "-" * 12 + "+"
    hdr = f"| {'Pipeline Stage':<30} | {'Duration (s)':>15} | {'% of Total':>10} |"
    
    print("\n" + sep)
    print(hdr)
    print(sep)
    
    stages = [
        ("1. Claim Extraction", stage1_time),
        (f"2. Evidence Search ({len(claims)} claims)", stage2_time),
        (f"3. Evidence Rating ({len(claims)} claims)", stage3_time),
        ("4. Overall Verdict Synthesis", stage4_time),
    ]

    for name, duration in stages:
        pct = (duration / total_time) * 100
        print(f"| {name:<30} | {duration:>13.2f} s | {pct:>9.1f}% |")

    print(sep)
    print(f"| {'Total End-to-End Time':<30} | {total_time:>13.2f} s | {'100.0%':>10} |")
    print(sep + "\n")

if __name__ == "__main__":
    main()
