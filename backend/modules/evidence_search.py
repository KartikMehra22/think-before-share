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

def _search_duckduckgo(query: str, max_results: int = 4) -> dict:
    """
    100% Free search engine using DuckDuckGo (requires zero API keys).
    Returns dict with 'snippets' and 'sources'.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        logger.info("search_evidence: executing DuckDuckGo (100%% Free Engine) query=%r", query)
        snippets = []
        sources = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for res in results:
                title = res.get("title", "")
                body = res.get("body", "")
                href = res.get("href", "")
                if body:
                    snippets.append(f"{title}: {body}"[:600])
                    sources.append(href)
        logger.info("search_evidence: DuckDuckGo returned snippets=%d sources=%d", len(snippets), len(sources))
        return {"snippets": snippets, "sources": sources}
    except Exception as exc:
        logger.warning("search_evidence: DuckDuckGo search failed err=%s", exc)
        return {"snippets": [], "sources": []}


def search_evidence(claim: str, search_query: str | None = None, max_results: int = 4) -> dict:
    """
    Search the web for evidence related to a factual claim.
    Dual Search Engine Architecture:
      1. Primary Free Engine: DuckDuckGo Search (100% Free, zero API key requirement).
      2. Secondary Engine: Tavily Search (if TAVILY_API_KEY is configured).
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

    # Build optimized search query
    if search_query and len(search_query.strip()) > 3:
        clean_keywords = search_query.replace('"', '').strip()
        query = f"fact check {clean_keywords}"
    else:
        clean_claim = claim.replace('"', '').replace("'", "").strip()
        query = f"fact check {clean_claim}"

    snippets = []
    sources = []

    # --- Engine 1: DuckDuckGo (100% Free & Keyless) ---
    logger.info("search_evidence: calling DuckDuckGo Free Search  claim=%.60s…", claim)
    ddg_res = _search_duckduckgo(query, max_results=max_results)
    snippets = ddg_res["snippets"]
    sources = ddg_res["sources"]

    # Retry DuckDuckGo with a shorter entity query if 0 results
    if not snippets:
        clean_claim_term = claim.replace('"', '').replace("'", "").strip()[:70]
        fallback_query = f"fact check {clean_claim_term}"
        logger.info("search_evidence: DuckDuckGo 0 hits — trying entity query=%r", fallback_query)
        ddg_res = _search_duckduckgo(fallback_query, max_results=max_results)
        snippets = ddg_res["snippets"]
        sources = ddg_res["sources"]

    # --- Engine 2: Tavily (Optional Secondary if configured and DDG had 0 hits) ---
    api_key = os.environ.get("TAVILY_API_KEY")
    if not snippets and api_key:
        logger.info("search_evidence: DuckDuckGo returned 0 hits — trying Tavily API...")
        t0 = time.monotonic()
        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
            )
            results_list = response.get("results", [])

            if response.get("answer"):
                snippets.append(f"Tavily Summary: {response['answer']}")
                sources.append("tavily-synthesis")

            for result in results_list:
                content = result.get("content", "").strip()
                url = result.get("url", "")
                if content:
                    snippets.append(content[:600])
                    sources.append(url)

            logger.info("search_evidence: Tavily returned in %.2fs snippets=%d", time.monotonic() - t0, len(snippets))
        except Exception as exc:
            logger.warning("search_evidence: Tavily search error. err=%s", exc)

    result_data = {"snippets": snippets, "sources": sources}

    if use_cache:
        cache = _load_cache()
        cache[normalized_claim] = result_data
        _save_cache(cache)

    return result_data


