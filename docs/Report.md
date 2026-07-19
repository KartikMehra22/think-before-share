# System Design Gap Analysis

I have reviewed the current codebase against your `system-design.md`. The project has fundamentally drifted from the intended architecture. You currently have a working monolithic prototype, but it does not adhere to the modular structure, error handling, or API design specified in the document.

Here is the exact breakdown of what is done, what is incomplete, and what is done improperly.

## 0. Folder Structure & Separation of Concerns
❌ **Improper:** The codebase is entirely flat. `main.py`, `llm.py`, `search.py`, and `transcript.py` are all in the root of `backend/`. 
- There is no `modules/` directory.
- There is no `prompts/` directory (prompts are hardcoded as strings in `llm.py`).
- M3, M5, M6, and M7 logic are all jammed into a single `llm.py` file.

## M1 — Video ID Resolver
⚠️ **Incomplete / Improper:** It works, but it's currently just a single regex function `extract_video_id` sitting inside `transcript.py` instead of having its own `modules/video_resolver.py`.

## M2 — Transcript Extractor
❌ **Improper Error Handling:** The design states that a missing transcript is an expected case, not a server error, and should return `status: "no_transcript"` (HTTP 200). 
- Currently, `transcript.py` raises a `ValueError` on failure, which `main.py` catches and turns into a hard `422 Unprocessable Entity` HTTP error, crashing the request pipeline.

## M3 — Claim Extractor
❌ **Improper Guardrails:** 
1. The design requires a hard limit of max 20 claims enforced **in code** (`claims[:20]`). This is completely missing.
2. The design requires that if the LLM extraction fails, it should return an empty array `[]` and let the rest of the flow degrade gracefully. Currently, `main.py` catches extraction errors and throws a `500 Internal Server Error`, crashing the request.

## M4 — Evidence Retriever
✅ **Mostly Done:** You actually have the caching working properly using `fixtures/search_cache.json`. It gracefully handles empty searches.

## M5 — Evidence Analyzer
❌ **Improper Guardrail:** The design states a **hard rule**: "if `sources` is empty (from M4), skip the LLM call entirely and return `status: "insufficient_evidence"` directly". 
- Currently, `main.py` unconditionally calls `rate_claim_with_evidence` even if no search snippets were found, forcing the LLM to guess from memory (risking hallucination).

## M6 — Media Literacy Insights
❌ **Not Done (Missing completely):** There is no code extracting media literacy signals (e.g., "emotional_wording") directly from the transcript. The current app only generates a generic 1-sentence tip at the very end.

## M7 — Evidence Map Aggregator
❌ **Improper:** The design strictly specifies that M7 must have **"No LLM call — pure counting/aggregation logic"**. 
- Currently, `get_overall_verdict` in `llm.py` makes a full Gemini API call to determine the verdict and write a literacy tip, instead of just aggregating the math (counting supported vs contradicted).

## M9 — Orchestration API (The Biggest Deviation)
❌ **Improper Architecture:** The design dictates a **polling architecture** where `POST /analyze` immediately returns a `{ "job_id": "..." }` and runs the pipeline in the background, while the frontend polls `GET /analyze/{job_id}` for progress updates.
- Currently, `POST /analyze` runs the entire pipeline synchronously in a single massive blocking request. This means the frontend hangs for 15-30 seconds waiting for all the LLM calls to finish, with no progress indication.

---

### Recommended Next Steps
If you want to realign with the `system-design.md`, we need to do a refactor. I recommend addressing them in this order:
1. **Refactor M9 to use Polling (Background Tasks):** This is the biggest architectural shift and will change how the frontend communicates with the backend.
2. **Restructure Folders:** Move functions into `modules/` and extract prompts into `prompts/`.
3. **Fix Error Handling & Guardrails (M2, M3, M5, M7):** Enforce the hard limits, stop throwing 422/500 errors for expected failures, and remove the LLM call from M7.
4. **Implement M6:** Build the missing Media Literacy Insights module.
