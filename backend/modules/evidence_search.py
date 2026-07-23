import os
import json
import time
import logging
from tavily import TavilyClient

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
CACHE_FILE = os.path.join(CACHE_DIR, "search_cache.json")

def _normalize_claim(claim: str) -> str:
    """Normalize the claim to use as a cache key by lowercasing and stripping whitespace."""
    return claim.strip().lower()

def _load_cache() -> dict:
    """Load the cache from search_cache.json, handling missing and malformed cases."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(
            "Failed to parse search cache file at %s: %s. Falling back to empty cache.",
            CACHE_FILE, e,
        )
        return {}

def _save_cache(cache: dict):
    """Save the cache dictionary to search_cache.json, creating parent directory if needed."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        logger.debug("search_cache: saved %d entries to disk", len(cache))
    except Exception as e:
        logger.warning("Failed to write search cache file at %s: %s", CACHE_FILE, e)

def search_evidence(claim: str, search_query: str | None = None, max_results: int = 4) -> dict:
    """
    Search the web for evidence related to a factual claim.
    Returns a dict with 'snippets' (list of str) and 'sources' (list of URLs).
    Caching is enabled by default unless USE_CACHE=false in environment variables.
    """
    use_cache_str = os.environ.get("USE_CACHE", "true").lower()
    use_cache = use_cache_str not in ("false", "0", "no")

    normalized_claim = _normalize_claim(claim)

    if use_cache:
        cache = _load_cache()
        if normalized_claim in cache:
            cached = cache[normalized_claim]
            logger.info(
                "search_evidence: CACHE HIT  snippets=%d  claim=%.60s…",
                len(cached.get("snippets", [])), claim,
            )
            return cached

    logger.info("search_evidence: CACHE MISS — calling Tavily  claim=%.60s…", claim)

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set in environment variables.")

    client = TavilyClient(api_key=api_key)

    # Build an optimized, non-quoted fact-checking query
    if search_query and len(search_query.strip()) > 3:
        clean_keywords = search_query.replace('"', '').strip()
        query = f"fact check {clean_keywords}"
    else:
        # Strip quote marks and unnecessary punctuation from full claim sentence
        clean_claim = claim.replace('"', '').replace("'", "").strip()
        query = f"fact check {clean_claim}"

    logger.debug("search_evidence: primary query=%r", query)

    t0 = time.monotonic()
    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )
    except Exception as exc:
        logger.error("search_evidence: Tavily primary search failed err=%s", exc)
        response = {}

    results_list = response.get("results", [])

    # Fallback retry if 0 results were found
    if not results_list and search_query:
        fallback_query = f"fact check {claim.replace('\"', '').strip()[:80]}"
        logger.info("search_evidence: 0 hits on primary query — trying fallback query=%r", fallback_query)
        try:
            response = client.search(
                query=fallback_query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
            )
            results_list = response.get("results", [])
        except Exception as exc:
            logger.error("search_evidence: Tavily fallback search failed err=%s", exc)

    tavily_elapsed = time.monotonic() - t0

    snippets = []
    sources = []

    # Include Tavily's synthesized answer if available
    if response.get("answer"):
        snippets.append(f"Tavily Summary: {response['answer']}")
        sources.append("tavily-synthesis")

    # Include individual search result snippets
    for result in results_list:
        content = result.get("content", "").strip()
        url = result.get("url", "")
        if content:
            snippets.append(content[:600])  # Limit each snippet
            sources.append(url)

    result_data = {"snippets": snippets, "sources": sources}
    logger.info(
        "search_evidence: Tavily returned in %.2fs  snippets=%d  sources=%d",
        tavily_elapsed,
        len(snippets),
        len([s for s in sources if s != "tavily-synthesis"]),
    )

    if use_cache:
        cache = _load_cache()
        cache[normalized_claim] = result_data
        _save_cache(cache)

    return result_data

