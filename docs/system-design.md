# Verify Before You Share — System Design v2

This is the build reference for the project. Every module has a fixed input/output shape, a home in the file structure, a "definition of done," and an owner. Read this before writing code for any module — the goal is that two people can build in parallel without ever breaking each other's work.

---

## 0. Folder Structure

Map every module to a real file now, so there's no ambiguity about where code goes.

```
verify-before-share/
├── backend/
│   ├── main.py                 # M9 — FastAPI app, /analyze endpoint
│   ├── modules/
│   │   ├── video_resolver.py   # M1
│   │   ├── transcript.py       # M2
│   │   ├── claims.py           # M3
│   │   ├── evidence_search.py  # M4
│   │   ├── evidence_analyze.py # M5
│   │   ├── insights.py         # M6
│   │   └── evidence_map.py     # M7
│   ├── prompts/
│   │   ├── claim_extractor.txt
│   │   ├── evidence_summarizer.txt
│   │   └── insights_analyzer.txt
│   ├── tests/
│   │   └── test_<module>.py    # one per module, run against fixtures below
│   ├── fixtures/
│   │   └── demo_transcript.json  # your real chosen demo video's transcript, saved once, reused everywhere
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   └── (Next.js app — M10, M8 UI)
└── docs/
    └── system-design.md        # this file
```

**Why fixtures matter:** save your real demo video's transcript to `fixtures/demo_transcript.json` on day 1. Every module downstream (M3–M7) should be tested against this *same real fixture*, not synthetic text — that way "works in testing" and "works in the actual pitch video" are the same thing.

---

## 1. Pipeline + Team Ownership

```
URL Input
   ↓
[M1] Video ID Resolver         ─┐
   ↓                            │  Owner A — DONE
[M2] Transcript Extractor      ─┘
   ↓
[M3] Claim Extractor            ─── Owner A (days 3–5)
   ↓
[M9] Orchestration API (thin)   ─── Owner A (day 5–6)
   ↓                    ↘
[M10] Frontend skeleton   [M6] Media Literacy Insights ─── Owner B (days 3–8, parallel, only needs M2's output)
   ↓ (Owner B, days 3–8)         ↓
[M4] Evidence Retriever ─── Owner A (days 7–9)
   ↓
[M5] Evidence Analyzer  ─── Owner A (days 9–11)
   ↓
[M7] Evidence Map Aggregator ─── either owner (day 12, trivial)
   ↓
[M8] Verify Before You Share ─── Owner B, mostly frontend (days 12–14)
```

**Split logic:** Owner A owns the harder sequential chain (transcript → claims → evidence, since each depends on the last). Owner B owns the frontend + the one backend module (M6) that only needs the transcript, so B is never blocked waiting on A's harder work.

---

## 2. Module Contracts

For each module: input, output, **HTTP/error behavior**, **definition of done**, and **environment variables** it needs.

### M1 — Video ID Resolver
- **File:** `backend/modules/video_resolver.py`
- **Input:** `url: str`
- **Output:** `{ "video_id": str, "url": str }`
- **Errors:** raises `InvalidURLError` if no pattern matches → M9 catches this and returns `400` with `{ "error": "invalid_url" }`
- **Env vars:** none
- **Definition of done:** unit test passes for `/watch?v=`, `/shorts/`, `youtu.be/`, `/embed/`, and one deliberately broken URL (must raise, not crash silently)
- **Status:** ✅ done

### M2 — Transcript Extractor
- **File:** `backend/modules/transcript.py`
- **Input:** `{ "video_id": str }`
- **Output:**
```json
{ "video_id": "...", "status": "ok", "transcript": "...", "segments": [...] }
```
or on failure:
```json
{ "video_id": "...", "status": "no_transcript", "transcript": null }
```
- **Errors:** never raise on missing captions — always return `status: "no_transcript"`. M9 turns this into `200` with the status flag, not a `500` — a missing transcript is an expected case, not a server error.
- **Env vars:** none
- **Definition of done:** returns correct transcript for your fixture video; returns `no_transcript` gracefully (not a crash) for a video you know has no captions
- **Status:** ✅ done

### M3 — Claim Extractor
- **File:** `backend/modules/claims.py`
- **Prompt file:** `backend/prompts/claim_extractor.txt`
- **Input:** `{ "transcript": str }`
- **Output:**
```json
{ "claims": [ { "id": "c1", "text": "...", "timestamp": 42.0 } ] }
```
- **Hard limit:** enforce max 20 claims **in code**, e.g. `claims[:20]`, even though the prompt also asks for a limit — never trust the model alone to bound output size.
- **Errors:** if LLM call fails or returns unparseable output, return `{ "claims": [], "status": "extraction_failed" }` rather than crashing the pipeline. M9 should let the rest of the flow degrade gracefully (empty evidence map) rather than 500ing the whole request.
- **Env vars:** `GEMINI_API_KEY`
- **Definition of done:** run against `fixtures/demo_transcript.json`, manually review the claim list once, confirm it's picking factual statements and skipping opinions/jokes. Re-tune the prompt against this exact fixture until satisfied — this is your actual demo output.

### M4 — Evidence Retriever
- **File:** `backend/modules/evidence_search.py`
- **Input:** `{ "claim": str }`
- **Output:**
```json
{ "claim": "...", "sources": [ { "title": "...", "url": "...", "snippet": "...", "domain": "..." } ] }
```
- **Caching (important given zero budget):** cache Tavily responses keyed by claim text during development — e.g. a simple local JSON file cache — so re-running tests doesn't burn your free-tier quota. Add a `USE_CACHE=true` env flag.
- **Errors:** if search returns zero results, return `{ "claim": "...", "sources": [] }` — never let this throw. M5 must handle empty `sources` explicitly (see below).
- **Env vars:** `TAVILY_API_KEY`, `USE_CACHE`
- **Definition of done:** returns ≥1 real source for at least 80% of claims from your fixture transcript; empty-source case tested explicitly with a deliberately obscure/fake claim.

### M5 — Evidence Analyzer
- **File:** `backend/modules/evidence_analyze.py`
- **Prompt file:** `backend/prompts/evidence_summarizer.txt`
- **Input:** `{ "claim": str, "sources": [...] }` (from M4)
- **Output:**
```json
{
  "claim": "...",
  "status": "supported | needs_context | contradicted | insufficient_evidence",
  "explanation": "...",
  "sources_used": ["url1", "url2"]
}
```
- **Hard rule:** if `sources` is empty (from M4), skip the LLM call entirely and return `status: "insufficient_evidence"` directly — don't let the model guess from memory when there's nothing to read. This is your main hallucination guardrail; enforce it in code, not just in the prompt.
- **Env vars:** `GEMINI_API_KEY`
- **Definition of done:** every one of the 4 status values has been observed at least once against real fixture claims — if you never see `contradicted` or `needs_context` in testing, your prompt or source quality needs work before demo day.

### M6 — Media Literacy Insights
- **File:** `backend/modules/insights.py`
- **Prompt file:** `backend/prompts/insights_analyzer.txt`
- **Input:** `{ "transcript": str }` — independent of M3/M4/M5
- **Output:**
```json
{ "signals": [ { "type": "emotional_wording", "example": "..." } ] }
```
- **Env vars:** `GEMINI_API_KEY`
- **Definition of done:** run against fixture transcript, confirm signals reference real phrases actually present in the transcript (spot-check 2–3 manually) — an ungrounded signal ("uses emotional wording" with no real example) is a credibility risk in front of judges.

### M7 — Evidence Map Aggregator
- **File:** `backend/modules/evidence_map.py`
- **Input:** array of M5 outputs + M6 output
- **Output:**
```json
{
  "total_claims": 6, "supported": 3, "needs_context": 2,
  "contradicted": 1, "insufficient_evidence": 0,
  "claims": [...], "signals": [...]
}
```
- **No LLM call** — pure counting/aggregation logic. Should have the simplest, most reliable test of any module.
- **Definition of done:** counts sum correctly to `total_claims` for any input, including empty input (all zeros, not a crash).

### M8 — Verify Before You Share
- Mostly frontend (Next.js component), consumes M7's shape directly.
- **Design rule (already agreed):** `Review Again` and `Share Anyway` are both non-blocking navigation actions — no backend gate, no "confirm" API call needed.

---

## 3. Orchestration API (M9) — Concrete Contract

**File:** `backend/main.py`

```
POST /analyze
Body: { "url": "https://youtube.com/..." }
```

**Progress strategy — decided now, not on day 15:** use **polling**, since it's far simpler to build and debug in a short timeline than streaming/websockets.

```
POST /analyze          → returns { "job_id": "..." } immediately, starts pipeline in background
GET  /analyze/{job_id} → returns current stage + partial results
```

Example polling response mid-pipeline:
```json
{
  "job_id": "abc123",
  "stage": "retrieving_evidence",
  "stages_complete": ["resolve_video", "transcript", "claims"],
  "result": null
}
```

Final response once done:
```json
{
  "job_id": "abc123",
  "stage": "done",
  "result": { /* M7 shape */ }
}
```

This lets the frontend show a real progress indicator ("Extracting claims... Checking evidence...") which also directly supports the "give us 10 seconds" framing from your pitch concept — the wait becomes part of the product's messaging, not dead time.

**Definition of done for M9:** a request with a known-good fixture URL reliably reaches `stage: "done"` with a fully populated result, and a request with a bad URL reaches a clean `error` stage without hanging or crashing the server.

---

## 4. Testing Checklist (run before touching the frontend polish)

- [ ] M1: 4 URL formats + 1 broken URL
- [ ] M2: fixture video works; known-no-caption video degrades cleanly
- [ ] M3: claim count ≤ 20 enforced in code; manual quality check against fixture
- [ ] M4: cache working (confirm second run doesn't hit the API again); empty-result case tested
- [ ] M5: all 4 status values observed at least once; empty-sources path never calls the LLM
- [ ] M6: signals reference real transcript text
- [ ] M7: counts always sum correctly, including the empty case
- [ ] M9: full pipeline reaches `done` on fixture URL end-to-end, timed (know your real total latency before demo day)
- [ ] Full run: time the entire pipeline against your actual demo video — if it's slow, decide now whether to pre-cache the full result for the live pitch or rely on live API calls

---

## 5. Environment Variables (single source of truth)

`.env.example`:
```
GEMINI_API_KEY=
TAVILY_API_KEY=
USE_CACHE=true
```

---

## Immediate Next Step

Owner A: build M3 against `fixtures/demo_transcript.json` (save that fixture first if you haven't). Owner B: start M6 in parallel against the same fixture, and start the M10 frontend skeleton against a hand-written mock of M9's polling response shape above — don't wait for M9 to actually exist to start the UI.
