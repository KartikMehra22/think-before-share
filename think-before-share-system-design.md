# Think Before You Share — System Design

This document breaks the project into modules, defines exactly what each one receives and produces, and gives a build order. The goal: build modules independently, but connect them with zero surprises because every interface is defined up front.

**Core rule:** every module takes a defined input shape and returns a defined output shape. If two modules agree on the shape in between them, it doesn't matter how either one is implemented internally.

---

## 0. Overall Pipeline

```
URL Input
   ↓
[M1] Video ID Resolver
   ↓
[M2] Transcript Extractor
   ↓
[M3] Claim Extractor
   ↓
[M4] Evidence Retriever  ──┐
   ↓                       │ (runs once per claim,
[M5] Evidence Analyzer  ←──┘  can be parallelized)
   ↓
[M6] Media Literacy Insights
   ↓
[M7] Evidence Map Aggregator
   ↓
[M8] Verify Before You Share Decision
```

Everything above sits behind one orchestration layer (M9) that the frontend (M10) talks to.

---

## Build Order (start here, in this order)

1. **M1 + M2** (Video ID Resolver + Transcript Extractor) — you already have this working
2. **M3** (Claim Extractor) — next, since M2's output feeds it directly
3. **M9** (Orchestration API) — build a thin FastAPI wrapper around M1→M3 *before* going further, so you have a real endpoint to test against and a real place to plug in M10
4. **M10** (Frontend skeleton) — connect to M9 early, even with fake/static data for later steps. This de-risks the frontend-backend integration early instead of leaving it for day 15.
5. **M4 + M5** (Evidence Retriever + Analyzer) — the hardest module, build once the pipeline around it already works end-to-end with stub data
6. **M6** (Media Literacy Insights) — independent, can be built in parallel with M4/M5 by the second team member
7. **M7** (Evidence Map Aggregator) — trivial once M5 and M6 exist
8. **M8** (Verify Before You Share) — last, purely a UI + aggregation step over M7's output

**Why this order:** M1–M3 and M9–M10 give you a thin, fully-connected pipeline fast — a "walking skeleton." Everything after that is filling in one module at a time without ever breaking the connections, because M9's contract to the frontend doesn't change even as M4–M8 get built behind it.

---

## Module Definitions

### M1 — Video ID Resolver
**Purpose:** Turn any accepted YouTube URL format into a clean video ID.
**Input:** raw URL string
**Output:**
```json
{ "video_id": "abc123XYZ90", "url": "original url" }
```
**Errors to handle:** invalid/unsupported URL → return a clear error object, never crash silently.
**Status:** done (regex-based resolver you already have).

---

### M2 — Transcript Extractor
**Purpose:** Get the full transcript text + timestamps for a video ID.
**Input:** `{ "video_id": "abc123XYZ90" }`
**Output:**
```json
{
  "video_id": "abc123XYZ90",
  "transcript": "full text as one string",
  "segments": [
    { "text": "...", "start": 0.0, "duration": 3.2 }
  ],
  "status": "ok" 
}
```
**Failure mode to design for now:** no captions available. Output should be:
```json
{ "video_id": "abc123XYZ90", "status": "no_transcript", "transcript": null }
```
Every downstream module must check `status` before assuming `transcript` exists — this is the #1 place demos break live.
**Status:** done.

---

### M3 — Claim Extractor
**Purpose:** Pull out factual, checkable claims from the transcript — ignore opinions/jokes.
**Input:** `{ "transcript": "full text" }`
**Output:**
```json
{
  "claims": [
    { "id": "c1", "text": "India has the highest literacy rate in the world.", "timestamp": 42.0 }
  ]
}
```
**Build note:** cap output at ~15–20 claims max (per the risk table) so a long transcript doesn't blow up later stages. Enforce this in the prompt AND in code (truncate the list even if the LLM ignores the instruction — never trust the LLM to self-limit).
**Where to start:** single specialized prompt, temperature low (0–0.3) for consistency. Test against your chosen demo video first — tune the prompt until claim count and quality feel right for *that specific video*, since that's what the pitch video will show.

---

### M4 — Evidence Retriever
**Purpose:** For one claim, search the web and return top trusted source pages.
**Input:** `{ "claim": "India has the highest literacy rate in the world." }`
**Output:**
```json
{
  "claim": "...",
  "sources": [
    { "title": "...", "url": "...", "snippet": "...", "domain": "unesco.org" }
  ]
}
```
**Where to start:** wire Tavily first with a hardcoded test claim, confirm you get usable results, *before* connecting it to M3's output. Isolate API integration risk from pipeline risk.
**Guardrail:** filter/rank by domain trust if possible (prefer .gov, .edu, major news, known fact-check orgs) — even a simple allow-list boost is enough for a prototype.

---

### M5 — Evidence Analyzer
**Purpose:** Given a claim + retrieved sources, decide the evidence category and write a plain-language explanation.
**Input:**
```json
{ "claim": "...", "sources": [ /* from M4 */ ] }
```
**Output:**
```json
{
  "claim": "...",
  "status": "supported | needs_context | contradicted | insufficient_evidence",
  "explanation": "plain language reasoning",
  "sources_used": [ "url1", "url2" ]
}
```
**Hard rule (from earlier in this project's design):** the LLM must only reason over the `sources` text passed in — never answer from its own memory. If sources are empty, status must default to `insufficient_evidence`, not a guess.

---

### M6 — Media Literacy Insights
**Purpose:** Flag observable communication signals in the transcript (not accusations).
**Input:** `{ "transcript": "full text" }` (independent of M4/M5 — can run in parallel)
**Output:**
```json
{
  "signals": [
    { "type": "emotional_wording", "example": "..." },
    { "type": "missing_citation", "example": "..." }
  ]
}
```
**Status:** can be built by teammate 2 while teammate 1 builds M4/M5 — no shared dependency except M2's transcript.

---

### M7 — Evidence Map Aggregator
**Purpose:** Combine all per-claim results into the summary view.
**Input:** the full list of M5 outputs + M6 output
**Output:**
```json
{
  "total_claims": 6,
  "supported": 3,
  "needs_context": 2,
  "contradicted": 1,
  "insufficient_evidence": 0,
  "claims": [ /* full M5 array */ ],
  "signals": [ /* M6 array */ ]
}
```
**Build note:** this is pure aggregation — no LLM call needed, just counting. Cheapest module to build, build it last so it can immediately consume real M5/M6 output.

---

### M8 — Verify Before You Share
**Purpose:** Turn M7's summary into the decision screen copy.
**Input:** M7 output
**Output:** UI-ready summary (can literally be M7's output rendered directly — this module may be almost entirely frontend, not backend).
**Design rule already agreed:** never block sharing — only present information. `[Review Again]` / `[Share Anyway]` both just navigate; no server-side gate.

---

### M9 — Orchestration API (FastAPI)
**Purpose:** Single entrypoint the frontend calls. Chains M1→M8 internally.
**Endpoint shape:**
```
POST /analyze
Body: { "url": "https://youtube.com/..." }

Response (progressive or final):
{
  "video_id": "...",
  "transcript_status": "ok",
  "claims": [...],
  "evidence_map": { ...M7 output... }
}
```
**Build note:** build this as a thin pass-through as early as possible (step 3 in build order) even before M4–M8 exist — have it return stub/mock data for those stages so M10 (frontend) can be built against a stable contract immediately.
**Progress reporting:** since the risk table already flags "slow response," consider either polling a `/status/{job_id}` endpoint or streaming stage updates — decide this now, not on day 15, since it affects how M10 is built.

---

### M10 — Frontend (Next.js)
**Purpose:** Render each stage as the pipeline completes: Video → Transcript → Claims → Evidence → Insights → Share Decision.
**Depends only on M9's contract**, never on individual backend modules directly. This is the whole point of M9 existing — the frontend should never need to change when you change how evidence retrieval works internally.
**Build note:** build against mocked M9 responses first (hardcode a fake JSON matching the contract above), so frontend work isn't blocked waiting for backend modules to be finished.

---

## Why This Prevents Errors

1. **Every module has a fixed input/output shape** — if M5's output format changes, only M7 needs to know; M1–M4 are unaffected.
2. **Failure states are defined per module, not discovered live** — especially M2's `no_transcript` case, which is the most likely thing to break during a live demo.
3. **The walking skeleton (M1→M3→M9→M10) exists before the hard module (M4/M5) is finished** — so you always have *something* fully connected and demoable, even if evidence retrieval is still being debugged on day 12.
4. **Two people can work in parallel without blocking each other**: one on M4/M5 (evidence), one on M6 + M10 (insights + frontend), because neither depends on the other — both only depend on M2/M3's already-finished output.

## Immediate Next Step

Build M3 (Claim Extractor) now, using the real transcript output you already have from your chosen demo video. Once you can see real claims coming out the other end, build the thin M9 endpoint wrapping M1→M3, and start M10 against it — that gives you a genuinely working, connected pipeline before touching the harder evidence-retrieval module.
